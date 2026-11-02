# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/escalation/transport.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The real transport of the escalation outbox.

Each queued escalation is wrapped in an `incident-transport/1` message (the contract of the development server: a message id, the
two node names, a nonce, the time and an HMAC-SHA256 over the canonical JSON of all of that) and posted over HTTP(S) to the address
the configuration names. The outbox only marks the item as sent when the receiver answers with a 2xx status AND a JSON body with
`"ok": true`; anything else (a refusal, a timeout, an unreachable link, a redirect) leaves it queued for the next flush.

Closed unless `transport.enabled` is true. The shared secret comes from an environment variable or a file outside the repository
and is never printed, logged or put in an error message. Plain `http://` is refused unless the host is loopback or the
configuration allows it explicitly.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from ..settings import TransportSettings
from .outbox import EscalationOutbox, QueuedEscalation

CONTRACT_VERSION = "incident-transport/1"
KIND_INCIDENT = "incident"
MIN_SECRET_LENGTH = 24


class TransportError(ValueError):
    """The transport is closed or misconfigured; nothing was sent."""


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_url(settings: TransportSettings) -> None:
    parts = urllib.parse.urlsplit(settings.url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise TransportError("transport.url must be an http(s) address with a host")
    if parts.scheme == "http" and not settings.allow_plain_http and not _is_loopback(parts.hostname):
        raise TransportError("transport.url is plain http to a host that is not loopback: use https or set allowPlainHttp")
    if parts.username or parts.password:
        raise TransportError("transport.url must not carry credentials")


def read_secret(settings: TransportSettings, environ: Mapping[str, str]) -> str:
    """The shared secret: the file when one is configured, else the environment variable. Never taken from the command line."""
    value = ""
    if settings.secret_file:
        try:
            value = Path(settings.secret_file).read_text(encoding="utf-8").strip()
        except OSError as error:
            raise TransportError(f"cannot read the transport secret file: {error.strerror or 'error'}") from error
    else:
        value = environ.get(settings.secret_env, "").strip()
    if len(value) < MIN_SECRET_LENGTH:
        raise TransportError(f"the transport secret is missing or shorter than {MIN_SECRET_LENGTH} characters")
    return value


def _signing_bytes(body: dict[str, Any]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_message(item: QueuedEscalation, settings: TransportSettings, secret: str, *, now: float | None = None) -> dict[str, Any]:
    """The signed message for one queued escalation. The message id is stable per escalation (a retry is recognisable as the
    same incident); the nonce and the time are new on every attempt."""
    body: dict[str, Any] = {
        "message_id": f"{settings.from_node}-{item.escalation_id}",
        "from_node": settings.from_node,
        "to_node": settings.to_node,
        "kind": KIND_INCIDENT,
        "contract_version": CONTRACT_VERSION,
        "nonce": secrets.token_hex(16),
        "sent_at": time.time() if now is None else now,
        "payload": {"escalationId": item.escalation_id, "evidenceBundle": item.payload},
    }
    body["mac"] = hmac.new(secret.encode("utf-8"), _signing_bytes(body), hashlib.sha256).hexdigest()
    return body


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:  # a redirect could carry the signed body somewhere else
        return None


class HttpSender:
    """`send(item) -> bool` for `EscalationOutbox.flush`: True only on a 2xx answer whose JSON body says `"ok": true`."""

    def __init__(self, settings: TransportSettings, secret: str, opener: Any = None) -> None:
        check_url(settings)
        self._settings = settings
        self._secret = secret
        self._opener = opener or urllib.request.build_opener(_NoRedirect)

    def __call__(self, item: QueuedEscalation) -> bool:
        message = build_message(item, self._settings, self._secret)
        data = json.dumps(message, sort_keys=True).encode("utf-8")
        if len(data) > self._settings.max_payload_bytes:
            return False  # too big for the receiver to accept by the configured limit: stays queued for a person to see
        request = urllib.request.Request(
            self._settings.url, data=data, method="POST",
            headers={"Content-Type": "application/json", "X-Hydra-Client": "technician"},
        )
        try:
            with self._opener.open(request, timeout=self._settings.timeout_seconds) as reply:
                if not 200 <= reply.status < 300:
                    return False
                answer = json.loads(reply.read(65536).decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            return False
        return isinstance(answer, dict) and answer.get("ok") is True


def send_pending(outbox: EscalationOutbox, settings: TransportSettings, environ: Mapping[str, str] | None = None, opener: Any = None) -> int:
    """Flushes the outbox over the configured transport; refuses when it is closed. Returns how many escalations were confirmed."""
    if not settings.enabled:
        raise TransportError("the transport is closed: set transport.enabled to true in the configuration file")
    secret = read_secret(settings, os.environ if environ is None else environ)
    return outbox.flush(HttpSender(settings, secret, opener))
