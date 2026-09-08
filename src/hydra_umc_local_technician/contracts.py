# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/contracts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real, stdlib-only validation for this project's own five minimal
contracts (the plan's own section 7, kept privately: ToolRequest,
ToolResult, MaintenanceProposal, EvidenceBundle, PatchVerificationReport).

The JSON Schema files under contracts/*.schema.json are normative - this
module gives an early, portable validation path before a generated
client exists, same convention HYDRA-UMC-SDK's own
clients/python/src/hydra_umc_sdk/validation.py already uses for its own
contracts. Every field name/requirement here is copied from those schema
files field-for-field, not reinterpreted.
"""
from __future__ import annotations

from typing import Any

from .policy.risk_levels import RiskLevel


class ContractValidationError(ValueError):
    """Raised when a payload violates a required contract invariant."""


_RISK_LEVEL_NAMES = {level.wire_name for level in RiskLevel}

REQUIRED: dict[str, tuple[str, ...]] = {
    "ToolRequest": ("schemaVersion", "requestId", "tool", "arguments", "riskLevel", "actor", "reason"),
    "ToolResult": ("requestId", "status", "output", "evidence", "timestamp", "durationMs", "toolVersion", "errorCode"),
    "MaintenanceProposal": (
        "diagnosis", "citedEvidence", "scope", "risk", "steps", "preChecks",
        "expectedChanges", "rollback", "confirmationRequired", "explicitLimits",
    ),
    "EvidenceBundle": (
        "componentVersions", "relevantManifests", "redactedLogExcerpts",
        "reproductionSteps", "failedTests", "impact", "actionsAttempted",
        "checksum", "date", "localValidationResult",
    ),
    "PatchVerificationReport": (
        "testedTarget", "preCheck", "appliedSteps", "healthChecks",
        "contractTests", "result", "rollbackExecuted", "promotionRecommended",
    ),
}


def _require_string(payload: dict[str, Any], name: str) -> None:
    if not isinstance(payload.get(name), str) or not payload[name]:
        raise ContractValidationError(f"{name} must be a non-empty string")


def _require_bool(payload: dict[str, Any], name: str) -> None:
    if not isinstance(payload.get(name), bool):
        raise ContractValidationError(f"{name} must be a real boolean")


def _require_list(payload: dict[str, Any], name: str, *, min_items: int = 0) -> None:
    value = payload.get(name)
    if not isinstance(value, list):
        raise ContractValidationError(f"{name} must be a list")
    if len(value) < min_items:
        raise ContractValidationError(f"{name} must have at least {min_items} item(s)")


def _validate_tool_request(payload: dict[str, Any]) -> None:
    if payload.get("schemaVersion") != "1.0":
        raise ContractValidationError("schemaVersion must be exactly '1.0'")
    _require_string(payload, "requestId")
    _require_string(payload, "tool")
    if not isinstance(payload.get("arguments"), dict):
        raise ContractValidationError("arguments must be an object")
    if payload.get("riskLevel") not in _RISK_LEVEL_NAMES:
        raise ContractValidationError(f"riskLevel must be one of {sorted(_RISK_LEVEL_NAMES)}")
    _require_string(payload, "actor")
    _require_string(payload, "reason")


def _validate_tool_result(payload: dict[str, Any]) -> None:
    _require_string(payload, "requestId")
    if payload.get("status") not in {"ok", "error", "denied"}:
        raise ContractValidationError("status must be one of 'ok', 'error', 'denied'")
    if not isinstance(payload.get("output"), dict):
        raise ContractValidationError("output must be an object")
    if not isinstance(payload.get("evidence"), str):
        raise ContractValidationError("evidence must be a string")
    _require_string(payload, "timestamp")
    duration = payload.get("durationMs")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0:
        raise ContractValidationError("durationMs must be a non-negative number")
    _require_string(payload, "toolVersion")
    error_code = payload.get("errorCode")
    if error_code is not None and not isinstance(error_code, str):
        raise ContractValidationError("errorCode must be a string or null")


def _validate_maintenance_proposal(payload: dict[str, Any]) -> None:
    _require_string(payload, "diagnosis")
    _require_list(payload, "citedEvidence", min_items=1)
    _require_string(payload, "scope")
    if payload.get("risk") not in _RISK_LEVEL_NAMES:
        raise ContractValidationError(f"risk must be one of {sorted(_RISK_LEVEL_NAMES)}")
    _require_list(payload, "steps", min_items=1)
    _require_list(payload, "preChecks")
    _require_list(payload, "expectedChanges")
    _require_string(payload, "rollback")
    _require_bool(payload, "confirmationRequired")
    _require_list(payload, "explicitLimits")


def _validate_evidence_bundle(payload: dict[str, Any]) -> None:
    if not isinstance(payload.get("componentVersions"), dict):
        raise ContractValidationError("componentVersions must be an object")
    _require_list(payload, "relevantManifests")
    _require_list(payload, "redactedLogExcerpts")
    _require_list(payload, "reproductionSteps", min_items=1)
    _require_list(payload, "failedTests")
    _require_string(payload, "impact")
    _require_list(payload, "actionsAttempted")
    _require_string(payload, "checksum")
    _require_string(payload, "date")
    _require_string(payload, "localValidationResult")


def _validate_patch_verification_report(payload: dict[str, Any]) -> None:
    target = payload.get("testedTarget")
    if not isinstance(target, dict):
        raise ContractValidationError("testedTarget must be an object")
    for field in ("package", "commit", "version"):
        _require_string(target, field)
    _require_string(payload, "preCheck")
    _require_list(payload, "appliedSteps")
    _require_list(payload, "healthChecks")
    _require_list(payload, "contractTests")
    if payload.get("result") not in {"passed", "failed", "inconclusive"}:
        raise ContractValidationError("result must be one of 'passed', 'failed', 'inconclusive'")
    _require_bool(payload, "rollbackExecuted")
    _require_bool(payload, "promotionRecommended")


_VALIDATORS = {
    "ToolRequest": _validate_tool_request,
    "ToolResult": _validate_tool_result,
    "MaintenanceProposal": _validate_maintenance_proposal,
    "EvidenceBundle": _validate_evidence_bundle,
    "PatchVerificationReport": _validate_patch_verification_report,
}


def validate(contract_name: str, payload: dict[str, Any]) -> None:
    """Raises ContractValidationError with a specific reason if `payload`
    does not satisfy `contract_name`. Returns None (does not raise) on a
    valid payload - mirrors HYDRA-UMC-SDK's own validate() signature."""
    if contract_name not in _VALIDATORS:
        raise ContractValidationError(f"unknown contract: {contract_name!r}")
    if not isinstance(payload, dict):
        raise ContractValidationError(f"{contract_name} payload must be a JSON object")
    missing = [key for key in REQUIRED[contract_name] if key not in payload]
    if missing:
        raise ContractValidationError(f"{contract_name} is missing required field(s): {', '.join(missing)}")
    extra = [key for key in payload if key not in REQUIRED[contract_name]]
    if extra:
        raise ContractValidationError(f"{contract_name} has unexpected field(s): {', '.join(extra)}")
    _VALIDATORS[contract_name](payload)
