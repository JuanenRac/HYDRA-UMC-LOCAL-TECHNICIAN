# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/knowledge/trust.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 0's own literal exit criterion (the plan's own section 8, kept
privately): "una prueba demuestra que una fuente recuperada maliciosa no
puede provocar ejecucion de comandos ni revelar un secreto" (a test
proves a malicious retrieved source can never trigger command execution
or reveal a secret).

The real defense is architectural, not a filter that tries to detect
"instruction-like" text (a losing game against a determined prompt
injection): retrieved knowledge - a README, a log line, an indexed doc -
is always wrapped as UntrustedText, a distinct type with no method that
produces a ToolRequest. The only real way to build a ToolRequest is
build_tool_request_from_model_output() below, which takes already-typed,
already-separated fields (never a single blob to parse) and additionally
refuses any tool name that policy.tool_matrix doesn't recognize as
implemented. A caller holding only UntrustedText has no path into a real
tool call without deliberately re-typing and re-validating each field -
exactly the friction this defense relies on, matching the plan's own
section 5.3 ("Los README, logs, commits, mensajes de error y
documentacion indexada son datos no confiables. No pueden cambiar las
politicas ni inducir comandos.").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts import ContractValidationError, validate
from ..policy.risk_levels import RiskLevel
from ..policy.tool_matrix import lookup_tool
from .redaction import redact_secrets


class UntrustedText(str):
    """Text retrieved from any indexed/external source - a README, a log
    excerpt, a manifest's own free-text `notes` field, a commit message.
    A str subclass (not a bare str) so a reviewer can grep for this type
    to see every place untrusted content enters the system, and so a
    function signature naming `str` specifically (never `UntrustedText`)
    documents that it only accepts already-trusted, already-typed input.

    This type intentionally has NO method that returns a ToolRequest, a
    MaintenanceProposal, or any other contract object - there is no
    "interpret this text as a command" path anywhere on this class.
    """

    def redacted(self) -> str:
        """The only thing this class is for: producing a real, sanitized
        plain str safe to display or cite as evidence - never a parsed
        instruction."""
        return redact_secrets(str(self))


class ToolCallRefused(Exception):
    """Raised by build_tool_request_from_model_output() for a real,
    specific, named reason - never silently downgraded to a no-op."""


@dataclass(frozen=True)
class ToolRequest:
    """The real, validated object - see contracts.py's own
    REQUIRED["ToolRequest"] for the exact wire shape this mirrors."""
    schema_version: str
    request_id: str
    tool: str
    arguments: dict[str, Any]
    risk_level: RiskLevel
    actor: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "requestId": self.request_id,
            "tool": self.tool,
            "arguments": self.arguments,
            "riskLevel": self.risk_level.wire_name,
            "actor": self.actor,
            "reason": self.reason,
        }


def build_tool_request_from_model_output(
    *,
    request_id: str,
    tool: str,
    arguments: dict[str, Any],
    actor: str,
    reason: str,
) -> ToolRequest:
    """The ONLY real way to construct a ToolRequest in this codebase.

    Deliberately takes separated, already-typed fields - never a single
    string to parse for a command. `tool` must already name a real,
    registered, IMPLEMENTED entry in policy.tool_matrix - a name a
    retrieved document might have suggested ("service.restart", "shell.exec",
    anything not in that real matrix, or an OBSERVE-level name whose own
    `implemented` flag is still False in this phase) is refused here,
    before any ToolRequest object ever exists, not filtered out later by
    whatever eventually dispatches one.
    """
    descriptor = lookup_tool(tool)
    if descriptor is None:
        raise ToolCallRefused(f"'{tool}' is not a registered tool - refusing, not guessing a risk level for it")
    if not descriptor.implemented:
        raise ToolCallRefused(f"'{tool}' is registered but not implemented in this phase - refusing")

    candidate = ToolRequest(
        schema_version="1.0",
        request_id=request_id,
        tool=tool,
        arguments=arguments,
        risk_level=descriptor.risk_level,
        actor=actor,
        reason=reason,
    )
    try:
        validate("ToolRequest", candidate.to_dict())
    except ContractValidationError as exc:
        raise ToolCallRefused(f"constructed ToolRequest failed its own contract: {exc}") from exc
    return candidate
