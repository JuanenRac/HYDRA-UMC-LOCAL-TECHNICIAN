# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/orchestrator/result_signing.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A ToolResult that says which tool made it and that this technician made it.

An EvidenceBundle is built from stored ToolResult files, and until now nothing tied a result to the tool the caller says it came
from (the caller declared the pair) or to this host (any JSON with the right shape was accepted). Here a result carries the name of its
`tool` and, when a key is configured, a `signature`: HMAC-SHA256 over the canonical JSON of the whole result (request id, tool, status,
output, evidence, timestamp, duration, version, error code). The key is a local secret outside the repository:
`HYDRA_UMC_LOCAL_TECHNICIAN_RESULT_KEY`, or `..._FILE` naming a file whose first line is the key (16 characters or more).

Without a key nothing is signed and nothing is refused, as before. With a key, building an evidence bundle refuses a result that is not
signed, whose signature does not verify, or whose tool is not the one it is presented for.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Mapping

KEY_VARIABLE = "HYDRA_UMC_LOCAL_TECHNICIAN_RESULT_KEY"
MIN_KEY_LENGTH = 16


class SignatureError(ValueError):
    """A ToolResult is not what it claims to be."""


def result_key(environ: Mapping[str, str] | None = None) -> bytes | None:
    """The configured key, or None when results are not signed. A key that is set but too short is an error, not 'unsigned'."""
    env = os.environ if environ is None else environ
    value = env.get(KEY_VARIABLE, "").strip()
    if not value:
        path = env.get(f"{KEY_VARIABLE}_FILE", "").strip()
        if path:
            try:
                value = Path(path).read_text(encoding="utf-8").splitlines()[0].strip()
            except (OSError, IndexError):
                value = ""
    if not value:
        return None
    if len(value) < MIN_KEY_LENGTH:
        raise SignatureError(f"{KEY_VARIABLE} must be at least {MIN_KEY_LENGTH} characters")
    return value.encode("utf-8")


def canonical(result: Mapping[str, Any]) -> bytes:
    body = {name: value for name, value in result.items() if name != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign(result: Mapping[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical(result), hashlib.sha256).hexdigest()


def verify(result: Mapping[str, Any], key: bytes, expected_tool: str | None = None) -> None:
    """Raises SignatureError unless the result is signed with `key` and (when given) made by `expected_tool`."""
    signature = result.get("signature")
    if not isinstance(signature, str) or not signature:
        raise SignatureError("the ToolResult is not signed")
    if expected_tool is not None and result.get("tool") != expected_tool:
        raise SignatureError(f"the ToolResult says it is from {result.get('tool')!r}, not {expected_tool!r}")
    if not hmac.compare_digest(sign(result, key), signature):
        raise SignatureError("the signature of the ToolResult does not verify")
