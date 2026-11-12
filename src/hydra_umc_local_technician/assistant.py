# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/assistant.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""An open, configurable assistant that writes advice for a person. It has no authority.

Any model behind an OpenAI-compatible chat endpoint can be used: the address, the model name, the key, the limits and the
system prompt are settings of the configuration file and nothing in the code names a model. The assistant is closed unless
`assistant.enabled` is a real `true`.

What it can and cannot do:

* the material it is given is redacted first and cut to `maxPromptChars`; a stored evidence bundle must still match its
  checksum, so an edited file is refused;
* by default only a loopback address is asked (`allowRemote`), plain http only to loopback unless `allowPlainHttp`, no
  credentials in the address and no redirects (a redirect could carry the material somewhere else);
* the answer is redacted again, stripped of control characters and cut to `maxResponseChars`; it is returned as text marked
  advisory. It is never parsed into a proposal, a step or an approval: a proposal still needs `propose_maintenance()` with
  evidence grounded in real tool results, and anything above OBSERVE still needs a signed approval.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .escalation.evidence import verify_bundle
from .knowledge.redaction import redact_secrets
from .settings import AssistantSettings

MIN_KEY_LENGTH = 8
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
DEFAULT_SYSTEM_PROMPT = (
    "You help a maintenance technician of an industrial machine read evidence. Answer in the language the user names. "
    "Say what the evidence shows, what is not shown by it and what a person could check next. You cannot run anything and "
    "you must not claim to have run anything. Do not invent values that are not in the evidence."
)
LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "de": "German", "fr": "French", "it": "Italian", "ja": "Japanese", "zh": "Chinese",
    "pt": "European Portuguese",
}

# (url, headers, body, timeout seconds) -> (status, body bytes); replaced by a stand-in in the tests
Transport = Callable[[str, Mapping[str, str], bytes, float], "tuple[int, bytes]"]


class AssistantError(ValueError):
    """The assistant is closed, misconfigured or its endpoint did not answer usefully; nothing is trusted."""


@dataclass(frozen=True)
class AssistantAnswer:
    text: str
    model: str
    truncated: bool
    advisory: bool = True  # always: the text is advice for a person, never a proposal or an approval


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_url(settings: AssistantSettings) -> None:
    parts = urllib.parse.urlsplit(settings.url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise AssistantError("assistant.url must be an http(s) address with a host")
    if parts.username or parts.password:
        raise AssistantError("assistant.url must not carry credentials")
    loopback = _is_loopback(parts.hostname)
    if not loopback and not settings.allow_remote:
        raise AssistantError("assistant.url is not a loopback address: set allowRemote to send the material to another machine")
    if parts.scheme == "http" and not loopback and not settings.allow_plain_http:
        raise AssistantError("assistant.url is plain http to a host that is not loopback: use https or set allowPlainHttp")


def read_key(settings: AssistantSettings, environ: Mapping[str, str]) -> str:
    """The key of the endpoint, if any: from the file when one is configured, else from the environment. Empty means none.

    Never taken from the command line and never printed. A local server often needs none; a key that is present but shorter than
    the minimum is refused rather than sent.
    """
    value = ""
    if settings.api_key_file:
        try:
            value = Path(settings.api_key_file).read_text(encoding="utf-8").strip()
        except OSError as error:
            raise AssistantError(f"cannot read the assistant key file: {error.strerror or 'error'}") from error
    else:
        value = environ.get(settings.api_key_env, "").strip()
    if value and len(value) < MIN_KEY_LENGTH:
        raise AssistantError(f"the assistant key is shorter than {MIN_KEY_LENGTH} characters")
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def http_transport(url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> "tuple[int, bytes]":
    request = urllib.request.Request(url, data=body, method="POST", headers=dict(headers))
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as reply:
            return reply.status, reply.read(2_000_000)
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        raise AssistantError(f"the assistant endpoint did not answer: {type(error).__name__}") from error


def material_from_bundle(bundle: Any) -> str:
    """The text a verified evidence bundle offers the assistant: the checksum must still be the one of its content."""
    steps = verify_bundle(bundle)
    parts = [f"Impact: {bundle['impact']}", "Local validation: " + bundle["localValidationResult"]]
    parts.append("Reproduction steps:\n" + "\n".join(f"- {step}" for step in steps))
    if bundle["failedTests"]:
        parts.append("Failed tests:\n" + "\n".join(f"- {name}" for name in bundle["failedTests"]))
    if bundle["actionsAttempted"]:
        parts.append("Actions already attempted:\n" + "\n".join(f"- {action}" for action in bundle["actionsAttempted"]))
    if bundle["redactedLogExcerpts"]:
        parts.append("Log excerpts:\n" + "\n---\n".join(bundle["redactedLogExcerpts"]))
    return "\n\n".join(parts)


def system_prompt(settings: AssistantSettings) -> str:
    if settings.system_prompt_file:
        try:
            text = Path(settings.system_prompt_file).read_text(encoding="utf-8").strip()
        except OSError as error:
            raise AssistantError(f"cannot read the system prompt file: {error.strerror or 'error'}") from error
        if not text:
            raise AssistantError("the system prompt file is empty")
        return text
    return DEFAULT_SYSTEM_PROMPT


def build_request(settings: AssistantSettings, material: str, question: str) -> dict[str, Any]:
    """The JSON body sent to the endpoint: redacted, cut to the limit and with the language the settings name."""
    if not question.strip():
        raise AssistantError("a question is needed")
    body = redact_secrets(material)
    cut = len(body) > settings.max_prompt_chars
    if cut:
        body = body[: settings.max_prompt_chars] + "\n[cut: the material was longer than the limit]"
    user = f"Language of the answer: {LANGUAGE_NAMES[settings.language]}.\n\nQuestion: {redact_secrets(question.strip())}\n\nMaterial:\n{body}"
    return {
        "model": settings.model,
        "messages": [{"role": "system", "content": system_prompt(settings)}, {"role": "user", "content": user}],
        "temperature": settings.temperature,
        "stream": False,
    }


def parse_answer(raw: bytes, settings: AssistantSettings) -> AssistantAnswer:
    try:
        reply = json.loads(raw.decode("utf-8"))
        content = reply["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
        raise AssistantError("the assistant endpoint answered in a shape that is not a chat completion") from error
    if not isinstance(content, str) or not content.strip():
        raise AssistantError("the assistant endpoint answered with no text")
    text = _CONTROL.sub("", redact_secrets(content)).strip()
    truncated = len(text) > settings.max_response_chars
    if truncated:
        text = text[: settings.max_response_chars] + " [cut]"
    return AssistantAnswer(text, settings.model, truncated)


def ask(
    settings: AssistantSettings,
    material: str,
    question: str,
    environ: Mapping[str, str] | None = None,
    transport: Transport | None = None,
) -> AssistantAnswer:
    """Ask the configured endpoint one question about `material`; refused when the assistant is closed."""
    if not settings.enabled:
        raise AssistantError("the assistant is closed: set assistant.enabled to true in the configuration file")
    check_url(settings)
    key = read_key(settings, os.environ if environ is None else environ)
    body = json.dumps(build_request(settings, material, question), sort_keys=True).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Hydra-Client": "technician"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    status, raw = (transport or http_transport)(settings.url, headers, body, settings.timeout_seconds)
    if not 200 <= status < 300:
        raise AssistantError(f"the assistant endpoint answered with status {status}")
    return parse_answer(raw, settings)
