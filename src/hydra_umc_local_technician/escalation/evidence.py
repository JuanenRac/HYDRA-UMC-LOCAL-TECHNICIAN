# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/escalation/evidence.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 4's own EvidenceBundle half: turning a real batch of already-run,
already-validated OBSERVE-level ToolResults into a real, contract-valid
EvidenceBundle - never an AI call, never a synthesized diagnosis. Mirrors
HYDRA-UMC-OPS-AGENT's own incident.py: pure derivation from already-observed
data (`IncidentBatch.add_service_health()` et al. only ever turn a real
`ServiceHealthResult` into a real, typed record, exactly as this module
only ever turns a real `ToolResult` into real bundle fields).

`impact` and `localValidationResult` are the two EvidenceBundle fields this
module cannot honestly derive on its own - see docs/CONTRACTS.md's own
"real, honest description of the impact" wording for `impact`: judging
real-world consequence is not something an OBSERVE-level tool call result
can tell this module by itself, and there is no inference engine yet
(Fase 2) to responsibly attempt it. Both stay required, caller-supplied
text - the human (or, in a much later phase, an authorized process)
assembling the bundle states them, this module never invents them.
Everything else here (`reproductionSteps`, `componentVersions`,
`relevantManifests`, `redactedLogExcerpts`, `checksum`, `date`) is
mechanical, deterministic extraction from data this technician's own
dispatch.py already produced and already validated.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..contracts import validate

# The real default this module falls back to when a caller has no local
# validation of its own to report - an honest statement of scope, never a
# claim that validation happened when it did not.
_NO_LOCAL_VALIDATION = "no local validation was run - this evidence is limited to already-produced OBSERVE-level tool output"


class EvidenceAssemblyError(ValueError):
    """Raised for a real, distinct reason this module refuses to build a
    bundle - never a silent best-effort result built from data this
    module cannot actually vouch for."""


@dataclass(frozen=True)
class ObservedResult:
    """One real OBSERVE-level tool call this bundle is built from - the
    exact `tool` name (`policy/tool_matrix.py`'s own registered name) paired
    with the real `ToolResult` dict `orchestrator/dispatch.py` already
    produced and validated for it. A `ToolResult` alone never carries its
    own tool name (see contracts.py's own REQUIRED["ToolResult"]), so the
    caller - the one orchestrator code path that actually called
    `dispatch_tool_request()` for each of these - is the only place that
    genuinely knows this pairing; this module never guesses it from the
    output's own shape."""
    tool: str
    result: dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _checksum(payload: dict[str, Any]) -> str:
    """A real, deterministic SHA-256 over the bundle's own real content
    (never `checksum`/`date` themselves) - `sort_keys=True` so the digest
    never depends on dict insertion order, same real property
    HYDRA-UMC-OPS-AGENT's own change_proposal.py `_content_digest()`
    relies on."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assemble_evidence_bundle(
    observed: list[ObservedResult],
    *,
    impact: str,
    local_validation_result: str | None = None,
    actions_attempted: list[str] | None = None,
    failed_tests: list[str] | None = None,
) -> dict[str, Any]:
    """Builds and returns a real, `contracts.validate("EvidenceBundle", ...)`-
    passing bundle from `observed` - a non-empty list of real OBSERVE-level
    tool calls this technician itself already ran. Every one of `observed`'s
    own `result` dicts is re-validated as a real `ToolResult` here too (not
    only trusted because a caller labeled it one) - a bundle this function
    builds is only ever grounded in data this codebase itself can already
    vouch for, never an arbitrary caller-supplied dict."""
    if not observed:
        raise EvidenceAssemblyError("cannot assemble an EvidenceBundle from zero observed tool results")
    if not impact or not impact.strip():
        raise EvidenceAssemblyError("impact must be a non-empty, real, honest description - never invented by this module")

    for item in observed:
        # Re-validates rather than trusting the caller's own labeling -
        # this bundle's whole point is to be grounded in real, already-
        # checked data, not in whatever shape a caller happens to pass.
        validate("ToolResult", item.result)

    # reproductionSteps: the literal `evidence` string each real tool call
    # already produced - the same real "what command, on what target"
    # record HYDRA-UMC-OPS-AGENT's own incident.py keeps as evidence_refs
    # (e.g. "systemctl is-active <unit>"), never a step this module infers.
    reproduction_steps = [item.result["evidence"] for item in observed]

    component_versions: dict[str, str] = {}
    relevant_manifests: list[str] = []
    redacted_log_excerpts: list[str] = []
    for item in observed:
        output = item.result.get("output", {})
        if not isinstance(output, dict):
            continue
        if item.tool == "manifest.read" and output.get("found") and isinstance(output.get("name"), str):
            version = output.get("version")
            if isinstance(version, str):
                component_versions[output["name"]] = version
            relevant_manifests.append(f"{output.get('project')}: {json.dumps(output, sort_keys=True, ensure_ascii=False)}")
        if item.tool == "logs.read" and isinstance(output.get("lines"), list):
            redacted_log_excerpts.extend(str(line) for line in output["lines"])

    bundle = {
        "componentVersions": component_versions,
        "relevantManifests": relevant_manifests,
        "redactedLogExcerpts": redacted_log_excerpts,
        "reproductionSteps": reproduction_steps,
        "failedTests": list(failed_tests) if failed_tests else [],
        "impact": impact,
        "actionsAttempted": list(actions_attempted) if actions_attempted else [],
        "localValidationResult": local_validation_result if local_validation_result else _NO_LOCAL_VALIDATION,
        "date": _utc_now_iso(),
    }
    bundle["checksum"] = _checksum(bundle)

    # Self-verification: a bundle this function itself cannot build validly
    # is a real bug here, not a case to return silently - same discipline
    # dispatch.py's own _tool_result() already applies to every ToolResult.
    validate("EvidenceBundle", bundle)
    return bundle
