# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/escalation/proposal.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 4's own MaintenanceProposal half.

This is deliberately NOT a generator that invents a diagnosis, steps or a
rollback plan from tool output on its own - there is no inference engine
in this codebase yet (Fase 2), and "the AI never gets authority by
generating a response" (this project's own non-negotiable principle,
repeated in every README and docs/SECURITY_MODEL.md) rules out a module
that would hand a fabricated remediation plan the same shape as a real
one. `propose_maintenance()` is instead a real, strict CONSTRUCTOR and
VALIDATOR: today, only a human operator can supply `diagnosis`/`steps`/
`rollback`; a much later phase's own inference engine could supply them
too, but even then the exact same grounding and confirmation rules below
still apply unchanged - this module does not get more trusting just
because the caller changed.

Mirrors HYDRA-UMC-OPS-AGENT's own change_proposal.py `propose_change()` in
spirit (a real constructor over already-supplied content, never a
synthesizer of it) but validates against THIS project's own normative
MaintenanceProposal contract (`contracts/*.schema.json` /
`contracts.py`), which has no lifecycle fields of its own (no
proposalId/status) - `contracts.validate()` rejects any field outside the
schema's own closed ten, so this module never adds one to the returned
payload itself.

The one real guardrail this module adds beyond bare contract validity:
`citedEvidence` must be grounded - every string in it must literally be
the `evidence` field of some already-produced, already-validated
`ToolResult` the caller passes as `evidence_pool` (the same real
`escalation.evidence.ObservedResult` list a caller would also hand to
`assemble_evidence_bundle()`). docs/CONTRACTS.md's own words for this
field are "never an unsupported claim" - enforcing that here, mechanically,
is the difference between a real guardrail and a comment asking a future
caller to please remember it.
"""
from __future__ import annotations

from typing import Any

from ..contracts import validate
from ..policy.risk_levels import POLICIES, RiskLevel
from .evidence import ObservedResult


class ProposalError(ValueError):
    """Raised for a real, distinct reason this module refuses to build a
    proposal."""


class UngroundedEvidenceError(ProposalError):
    """A `citedEvidence` entry does not match any real, already-observed
    tool result's own `evidence` field - refused before the proposal is
    ever built, not accepted and merely flagged."""


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProposalError(f"{field_name} must be a non-empty string")


def propose_maintenance(
    *,
    diagnosis: str,
    cited_evidence: list[str],
    evidence_pool: list[ObservedResult],
    scope: str,
    risk: RiskLevel,
    steps: list[str],
    rollback: str,
    pre_checks: list[str] | None = None,
    expected_changes: list[str] | None = None,
    explicit_limits: list[str] | None = None,
) -> dict[str, Any]:
    """Builds and returns a real, `contracts.validate("MaintenanceProposal", ...)`-
    passing proposal. Never executes anything - a proposal this function
    returns is exactly what docs/CONTRACTS.md already says it is: "always
    shown to a human before anything past it happens." Nothing in this
    codebase (Fase 3's own OBSERVE-only TOOL_MATRIX, Fase 4's own scope) can
    act on a MaintenanceProposal at all yet; that stays true regardless of
    this proposal's own declared `risk`."""
    _require_non_empty(diagnosis, "diagnosis")
    _require_non_empty(scope, "scope")
    _require_non_empty(rollback, "rollback")
    if not cited_evidence:
        raise ProposalError("citedEvidence must have at least one entry - a diagnosis with no cited evidence is an unsupported claim")
    if not steps:
        raise ProposalError("steps must have at least one entry")
    if not isinstance(risk, RiskLevel):
        raise ProposalError(f"risk must be a real RiskLevel, got {type(risk).__name__}")

    real_evidence_strings = {item.result["evidence"] for item in evidence_pool}
    ungrounded = [entry for entry in cited_evidence if entry not in real_evidence_strings]
    if ungrounded:
        raise UngroundedEvidenceError(
            f"citedEvidence contains {len(ungrounded)} entr{'y' if len(ungrounded) == 1 else 'ies'} not backed by any "
            f"real, already-observed tool result: {ungrounded!r}"
        )

    # confirmationRequired is never a caller-supplied boolean - it is
    # exactly what this project's own risk-level policy already says for
    # `risk` (policy/risk_levels.py's own POLICIES), so a proposal can
    # never silently imply confirmation is optional by construction.
    confirmation_required = POLICIES[risk].requires_confirmation

    proposal = {
        "diagnosis": diagnosis,
        "citedEvidence": list(cited_evidence),
        "scope": scope,
        "risk": risk.wire_name,
        "steps": list(steps),
        "preChecks": list(pre_checks) if pre_checks else [],
        "expectedChanges": list(expected_changes) if expected_changes else [],
        "rollback": rollback,
        "confirmationRequired": confirmation_required,
        "explicitLimits": list(explicit_limits) if explicit_limits else [],
    }

    # Self-verification, same discipline as escalation.evidence's own
    # assemble_evidence_bundle() and dispatch.py's own _tool_result().
    validate("MaintenanceProposal", proposal)
    return proposal
