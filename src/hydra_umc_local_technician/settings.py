# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/settings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The five optional sections of the configuration file that switch on the escalation transport, the runbook rules, the signed
approvals and the periodic baseline snapshot.

Every section is closed unless its `enabled` switch is a real `true`; a key this module does not know is an error (a typo must not
silently leave a safety setting at a different value), and every tuned number lives here, in the file, never in the code.

    "transport": {"enabled": false, "url": "https://...", "fromNode": "technician-1", "toNode": "dev-server",
                  "secretEnv": "HYDRA_UMC_LOCAL_TECHNICIAN_TRANSPORT_SECRET", "secretFile": "/etc/.../secret",
                  "timeoutSeconds": 10, "allowPlainHttp": false, "maxPayloadBytes": 1000000}
    "runbooks": {"enabled": false, "directory": "/etc/.../runbooks", "language": "en"}
    "approvals": {"enabled": false, "trustStore": "/etc/.../trust.json", "maxValiditySeconds": 900, "usedNonces": "/var/.../nonces.json"}
    "snapshot": {"enabled": false, "directory": "/var/.../baselines", "keep": 48}
    "knowledge": {"enabled": false, "directory": "/var/.../index", "maxStoredFiles": 4096}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SETTINGS_KEYS = ("transport", "runbooks", "approvals", "snapshot", "knowledge")
LANGUAGES = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class SettingsError(ValueError):
    """A section of the configuration file is malformed."""


@dataclass(frozen=True)
class TransportSettings:
    enabled: bool = False
    url: str = ""
    from_node: str = ""
    to_node: str = ""
    secret_env: str = "HYDRA_UMC_LOCAL_TECHNICIAN_TRANSPORT_SECRET"
    secret_file: str = ""
    timeout_seconds: float = 10.0
    allow_plain_http: bool = False
    max_payload_bytes: int = 1_000_000
    # The token of THIS node for the receiving server (issued by `node-token issue` there). With require_node_token on (the
    # default) a send without a readable token is refused before anything leaves; off, the message goes without the header.
    node_token_file: str = ""
    require_node_token: bool = True


@dataclass(frozen=True)
class RunbookSettings:
    enabled: bool = False
    directory: str = ""
    language: str = "en"


@dataclass(frozen=True)
class ApprovalSettings:
    enabled: bool = False
    trust_store: str = ""
    max_validity_seconds: int = 900
    used_nonces: str = ""


@dataclass(frozen=True)
class SnapshotSettings:
    enabled: bool = False
    directory: str = ""
    keep: int = 48


@dataclass(frozen=True)
class KnowledgeSettings:
    """The index of the knowledge sources kept on disk between runs (off: it lives in the process only)."""

    enabled: bool = False
    directory: str = ""
    max_stored_files: int = 4096


@dataclass(frozen=True)
class Settings:
    transport: TransportSettings = TransportSettings()
    runbooks: RunbookSettings = RunbookSettings()
    approvals: ApprovalSettings = ApprovalSettings()
    snapshot: SnapshotSettings = SnapshotSettings()
    knowledge: KnowledgeSettings = KnowledgeSettings()


def _section(raw: dict[str, Any], name: str, allowed: set[str]) -> dict[str, Any]:
    section = raw.get(name, {})
    if not isinstance(section, dict):
        raise SettingsError(f'"{name}" must be an object')
    unknown = sorted(set(section) - allowed)
    if unknown:
        raise SettingsError(f'unknown "{name}" key(s): {", ".join(unknown)}')
    if not isinstance(section.get("enabled", False), bool):
        raise SettingsError(f'"{name}.enabled" must be true or false')
    return section


def _text(section: dict[str, Any], name: str, key: str, default: str, *, absolute: bool = False) -> str:
    value = section.get(key, default)
    if not isinstance(value, str):
        raise SettingsError(f'"{name}.{key}" must be a string')
    if absolute and value and not Path(value).is_absolute():
        raise SettingsError(f'"{name}.{key}" must be an absolute path')
    return value


def _number(section: dict[str, Any], name: str, key: str, default: float, low: float, high: float, *, integer: bool) -> Any:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (integer and not isinstance(value, int)):
        raise SettingsError(f'"{name}.{key}" must be {"an integer" if integer else "a number"}')
    if not low <= value <= high:
        raise SettingsError(f'"{name}.{key}" must be from {low} to {high}')
    return value


def parse_settings(raw: object) -> Settings:
    """Reads the four sections out of a whole configuration object (the other keys are not this module's business)."""
    if not isinstance(raw, dict):
        raise SettingsError("the config must be a JSON object")
    t = _section(raw, "transport", {"enabled", "url", "fromNode", "toNode", "secretEnv", "secretFile", "timeoutSeconds", "allowPlainHttp", "maxPayloadBytes", "nodeTokenFile", "requireNodeToken"})
    if not isinstance(t.get("allowPlainHttp", False), bool):
        raise SettingsError('"transport.allowPlainHttp" must be true or false')
    if not isinstance(t.get("requireNodeToken", True), bool):
        raise SettingsError('"transport.requireNodeToken" must be true or false')
    transport = TransportSettings(
        enabled=t.get("enabled", False), url=_text(t, "transport", "url", ""), from_node=_text(t, "transport", "fromNode", ""),
        to_node=_text(t, "transport", "toNode", ""), secret_env=_text(t, "transport", "secretEnv", TransportSettings.secret_env),
        secret_file=_text(t, "transport", "secretFile", "", absolute=True),
        timeout_seconds=float(_number(t, "transport", "timeoutSeconds", 10, 1, 120, integer=False)),
        allow_plain_http=t.get("allowPlainHttp", False),
        max_payload_bytes=_number(t, "transport", "maxPayloadBytes", 1_000_000, 1024, 20_000_000, integer=True),
        node_token_file=_text(t, "transport", "nodeTokenFile", "", absolute=True), require_node_token=t.get("requireNodeToken", True),
    )
    if transport.enabled and not (transport.url and transport.from_node and transport.to_node):
        raise SettingsError('"transport" needs "url", "fromNode" and "toNode" when it is enabled')
    if transport.enabled and transport.require_node_token and not transport.node_token_file:
        raise SettingsError('"transport" needs "nodeTokenFile" when it is enabled, or "requireNodeToken": false')
    r = _section(raw, "runbooks", {"enabled", "directory", "language"})
    runbooks = RunbookSettings(
        enabled=r.get("enabled", False), directory=_text(r, "runbooks", "directory", "", absolute=True),
        language=_text(r, "runbooks", "language", "en"),
    )
    if runbooks.language not in LANGUAGES:
        raise SettingsError(f'"runbooks.language" must be one of {", ".join(LANGUAGES)}')
    if runbooks.enabled and not runbooks.directory:
        raise SettingsError('"runbooks" needs "directory" when it is enabled')
    a = _section(raw, "approvals", {"enabled", "trustStore", "maxValiditySeconds", "usedNonces"})
    approvals = ApprovalSettings(
        enabled=a.get("enabled", False), trust_store=_text(a, "approvals", "trustStore", "", absolute=True),
        max_validity_seconds=_number(a, "approvals", "maxValiditySeconds", 900, 30, 86_400, integer=True),
        used_nonces=_text(a, "approvals", "usedNonces", "", absolute=True),
    )
    if approvals.enabled and not approvals.trust_store:
        raise SettingsError('"approvals" needs "trustStore" when it is enabled')
    s = _section(raw, "snapshot", {"enabled", "directory", "keep"})
    snapshot = SnapshotSettings(
        enabled=s.get("enabled", False), directory=_text(s, "snapshot", "directory", "", absolute=True),
        keep=_number(s, "snapshot", "keep", 48, 1, 10_000, integer=True),
    )
    if snapshot.enabled and not snapshot.directory:
        raise SettingsError('"snapshot" needs "directory" when it is enabled')
    k = _section(raw, "knowledge", {"enabled", "directory", "maxStoredFiles"})
    knowledge = KnowledgeSettings(
        enabled=k.get("enabled", False), directory=_text(k, "knowledge", "directory", "", absolute=True),
        max_stored_files=_number(k, "knowledge", "maxStoredFiles", 4096, 1, 100_000, integer=True),
    )
    if knowledge.enabled and not knowledge.directory:
        raise SettingsError('"knowledge" needs "directory" when it is enabled')
    return Settings(transport, runbooks, approvals, snapshot, knowledge)


def load_settings(config_path: str | None) -> Settings:
    """The settings of a configuration file; without a file everything is closed."""
    if config_path is None:
        return Settings()
    return parse_settings(json.loads(Path(config_path).read_text(encoding="utf-8")))
