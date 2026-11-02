# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/policy/approvals.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Ed25519 signed approvals and the store of trusted public keys.

A person approves ONE action on ONE exact proposal by signing a small document (approver alias, action, the SHA-256 of the
canonical proposal, issue and expiry time, a nonce) with a private key that never leaves the approver's own machine. This host
holds only a trust store of PUBLIC keys, one per alias, imported and exported as small files and checked by fingerprint. A
verified approval becomes the `ApprovalRecord(signature_verified=True)` that `policy.execution_mode.decide()` asks for; any
failure (unknown alias, bad signature, another proposal, another action, expired, validity longer than the configured maximum, a
nonce already used) is an `ApprovalError` and nothing is approved.

Needs the optional `cryptography` package (the `approvals` extra); without it every call here says so instead of degrading to a
weaker check. Private keys are written outside any git working tree and with owner-only permissions where the system has them.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .execution_mode import ApprovalRecord

DOMAIN = b"hydra-umc-local-technician/approval/1\n"
CLOCK_SKEW_SECONDS = 60.0
_ALIAS_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


class ApprovalError(ValueError):
    """The approval or the trust store is not acceptable; nothing is approved."""


def _crypto() -> Any:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as error:
        raise ApprovalError("signed approvals need the 'cryptography' package: install the 'approvals' extra") from error
    return ed25519, InvalidSignature


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str, what: str, length: int | None = None) -> bytes:
    try:
        raw = base64.b64decode(text.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as error:
        raise ApprovalError(f"{what} is not valid base64") from error
    if length is not None and len(raw) != length:
        raise ApprovalError(f"{what} must be {length} bytes")
    return raw


def check_alias(alias: str) -> str:
    if not alias or len(alias) > 64 or not set(alias) <= _ALIAS_CHARS:
        raise ApprovalError("an alias is 1 to 64 letters, digits, dot, dash or underscore")
    return alias


def fingerprint(public_key_b64: str) -> str:
    """SHA-256 of the raw public key, in groups of four, for a person to compare by eye or by voice."""
    digest = hashlib.sha256(_unb64(public_key_b64, "the public key", 32)).hexdigest()
    return " ".join(digest[i:i + 4] for i in range(0, 32, 4))


def proposal_digest(proposal: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(proposal, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _inside_git_tree(path: Path) -> bool:
    return any((parent / ".git").exists() for parent in [path.resolve().parent, *path.resolve().parent.parents])


def _write_private(path: Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def generate_keypair(private_path: Path, public_path: Path, alias: str) -> str:
    """Creates a new key pair. The private file is refused inside a git working tree, never overwritten, and owner-only. Returns
    the fingerprint of the public key."""
    ed25519, _ = _crypto()
    check_alias(alias)
    if _inside_git_tree(private_path):
        raise ApprovalError("the private key must be outside any git working tree")
    if private_path.exists() or public_path.exists():
        raise ApprovalError("a key file already exists there: nothing was overwritten")
    private = ed25519.Ed25519PrivateKey.generate()
    raw_private = private.private_bytes_raw()
    public_b64 = _b64(private.public_key().public_bytes_raw())
    private_path.parent.mkdir(parents=True, exist_ok=True)
    _write_private(private_path, _b64(raw_private) + "\n")
    _write_json(public_path, {"alias": alias, "algorithm": "ed25519", "publicKey": public_b64, "fingerprint": fingerprint(public_b64)})
    return fingerprint(public_b64)


@dataclass
class TrustStore:
    """alias -> public key (base64). Stored as JSON; nothing secret is ever in it."""

    path: Path
    keys: dict[str, str]

    @staticmethod
    def load(path: Path) -> "TrustStore":
        if not path.exists():
            return TrustStore(path, {})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ApprovalError(f"the trust store cannot be read: {error}") from error
        keys = raw.get("keys") if isinstance(raw, dict) else None
        if not isinstance(keys, dict) or raw.get("version") != 1:
            raise ApprovalError("the trust store must be an object with version 1 and a 'keys' object")
        for alias, value in keys.items():
            check_alias(alias)
            if not isinstance(value, str):
                raise ApprovalError(f"the key of {alias!r} must be a string")
            _unb64(value, f"the key of {alias!r}", 32)
        return TrustStore(path, dict(keys))

    def save(self) -> None:
        _write_json(self.path, {"version": 1, "keys": self.keys})

    def add(self, alias: str, public_key_b64: str, *, replace: bool = False) -> str:
        """Trusts a public key under an alias. An alias already in the store is never silently re-pointed to another key."""
        check_alias(alias)
        _unb64(public_key_b64, "the public key", 32)
        if alias in self.keys and self.keys[alias] != public_key_b64 and not replace:
            raise ApprovalError(f"the alias {alias!r} already trusts another key: remove it first (or replace explicitly)")
        self.keys[alias] = public_key_b64
        self.save()
        return fingerprint(public_key_b64)

    def remove(self, alias: str) -> None:
        if alias not in self.keys:
            raise ApprovalError(f"no key is trusted under {alias!r}")
        del self.keys[alias]
        self.save()

    def export(self, alias: str, destination: Path) -> None:
        if alias not in self.keys:
            raise ApprovalError(f"no key is trusted under {alias!r}")
        _write_json(destination, {"alias": alias, "algorithm": "ed25519", "publicKey": self.keys[alias], "fingerprint": fingerprint(self.keys[alias])})


def read_public_key_file(path: Path) -> tuple[str, str]:
    """(alias, public key) of a file made by `generate_keypair` or `TrustStore.export`; a stated fingerprint must match."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ApprovalError(f"the public key file cannot be read: {error}") from error
    if not isinstance(raw, dict) or raw.get("algorithm") != "ed25519" or not isinstance(raw.get("publicKey"), str):
        raise ApprovalError("the public key file must hold an ed25519 'publicKey'")
    if "fingerprint" in raw and raw["fingerprint"] != fingerprint(raw["publicKey"]):
        raise ApprovalError("the fingerprint in the file is not that of its key")
    return str(raw.get("alias", "")), raw["publicKey"]


def sign_approval(private_path: Path, approver: str, action: str, proposal: dict[str, Any], *, ttl_seconds: int, now: float | None = None) -> dict[str, Any]:
    """Run by the approver, on the approver's machine, with the private key. Returns the signed approval document."""
    ed25519, _ = _crypto()
    check_alias(approver)
    if not action.strip():
        raise ApprovalError("the action must be named")
    if ttl_seconds <= 0:
        raise ApprovalError("the validity must be positive")
    try:
        private = ed25519.Ed25519PrivateKey.from_private_bytes(_unb64(private_path.read_text(encoding="utf-8").strip(), "the private key", 32))
    except OSError as error:
        raise ApprovalError(f"the private key cannot be read: {error.strerror or 'error'}") from error
    issued = time.time() if now is None else now
    body = {"version": 1, "approver": approver, "action": action, "proposalSha256": proposal_digest(proposal),
            "issuedAt": issued, "expiresAt": issued + ttl_seconds, "nonce": secrets.token_hex(16)}
    return {**body, "signature": _b64(private.sign(DOMAIN + _canonical(body)))}


def _canonical(body: dict[str, Any]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_nonces(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ApprovalError(f"the used-nonces file cannot be read: {error}") from error
    if not isinstance(data, dict) or not all(isinstance(v, (int, float)) for v in data.values()):
        raise ApprovalError("the used-nonces file must map nonce -> expiry time")
    return {str(k): float(v) for k, v in data.items()}


def verify_approval(
    approval: dict[str, Any], proposal: dict[str, Any], action: str, store: TrustStore, *,
    max_validity_seconds: int, used_nonces: Path | None = None, now: float | None = None,
) -> ApprovalRecord:
    """The `ApprovalRecord` for a valid approval of exactly this action on exactly this proposal, or an `ApprovalError`."""
    _, invalid_signature = _crypto()
    ed25519, _ = _crypto()
    fields = ("version", "approver", "action", "proposalSha256", "issuedAt", "expiresAt", "nonce")
    if not isinstance(approval, dict) or any(key not in approval for key in (*fields, "signature")) or set(approval) - {*fields, "signature"}:
        raise ApprovalError("the approval does not have the documented fields")
    body = {key: approval[key] for key in fields}
    issued, expires = body["issuedAt"], body["expiresAt"]
    if body["version"] != 1 or not all(isinstance(v, str) for v in (body["approver"], body["action"], body["proposalSha256"], body["nonce"], approval["signature"])):
        raise ApprovalError("the approval has the wrong version or field types")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (issued, expires)):
        raise ApprovalError("the approval times must be numbers")
    alias = body["approver"]
    public = store.keys.get(alias)
    if public is None:
        raise ApprovalError(f"nobody is trusted under the alias {alias!r}")
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(_unb64(public, "the trusted key", 32)).verify(
            _unb64(approval["signature"], "the signature", 64), DOMAIN + _canonical(body))
    except invalid_signature as error:
        raise ApprovalError("the signature does not match the trusted key") from error
    if body["action"] != action:
        raise ApprovalError(f"the approval is for {body['action']!r}, not {action!r}")
    if body["proposalSha256"] != proposal_digest(proposal):
        raise ApprovalError("the approval was signed for another proposal")
    at = time.time() if now is None else now
    if expires - issued > max_validity_seconds:
        raise ApprovalError(f"the approval is valid for longer than the {max_validity_seconds} seconds the configuration allows")
    if at < issued - CLOCK_SKEW_SECONDS:
        raise ApprovalError("the approval is dated in the future")
    if at > expires:
        raise ApprovalError("the approval has expired")
    if used_nonces is not None:
        seen = {nonce: until for nonce, until in _load_nonces(used_nonces).items() if until >= at}
        if body["nonce"] in seen:
            raise ApprovalError("this approval was already used")
        seen[body["nonce"]] = float(expires)
        _write_json(used_nonces, seen)
    return ApprovalRecord(approved_by=alias, action=action, signature_verified=True)
