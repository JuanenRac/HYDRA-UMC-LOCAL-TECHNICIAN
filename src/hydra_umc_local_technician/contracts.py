# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/contracts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real, stdlib-only validation for this project's own five minimal
contracts (ToolRequest, ToolResult, MaintenanceProposal, EvidenceBundle,
PatchVerificationReport).

The JSON Schema files under contracts/*.schema.json are normative - this
module gives an early, portable validation path before a generated
client exists, same convention HYDRA-UMC-SDK's own
clients/python/src/hydra_umc_sdk/validation.py already uses for its own
contracts. Every field name/requirement here is copied from those schema
files field-for-field, not reinterpreted.
"""
from __future__ import annotations

import math
from datetime import datetime
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


def _require_iso_timestamp(payload: dict[str, Any], name: str) -> None:
    """both `ToolResult.timestamp` and `EvidenceBundle.date`
    declare `"type": "string", "format": "date-time"` in their normative
    contracts/*.schema.json - but a JSON Schema validator does not
    enforce `format` by default (it requires an explicit format-checking
    plugin/flag to be turned on), and this hand-written Python validator
    never checked it at all, treating it as an ordinary non-empty string.
    `datetime.fromisoformat()` (Python 3.11+, which this project already
    requires) accepts RFC 3339 date-time strings including a trailing
    'Z', so this enforces the same policy the schema already declares
    without introducing a new one.
    """
    _require_string(payload, name)
    try:
        datetime.fromisoformat(payload[name])
    except ValueError:
        raise ContractValidationError(f"{name} must be a valid ISO-8601/RFC-3339 date-time, got {payload[name]!r}") from None


def _require_list(payload: dict[str, Any], name: str, *, min_items: int = 0) -> None:
    value = payload.get(name)
    if not isinstance(value, list):
        raise ContractValidationError(f"{name} must be a list")
    if len(value) < min_items:
        raise ContractValidationError(f"{name} must have at least {min_items} item(s)")
    # this used to only check the container's own type/length,
    # never a single element inside it - every one of this contract's
    # own list fields declares `"items": {"type": "string"}` in its
    # normative contracts/*.schema.json (no minLength on the item
    # itself, so an empty string is schema-valid and deliberately not
    # rejected here either), but nothing on the Python side actually
    # enforced that a list entry was ever a string at all. A number,
    # null, or nested object anywhere in the list used to sail through
    # silently.
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ContractValidationError(f"{name}[{index}] must be a string, got {type(item).__name__}")


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
    _require_iso_timestamp(payload, "timestamp")
    duration = payload.get("durationMs")
    # `duration < 0` alone is not a finiteness check - NaN compares
    # False against everything, so a NaN durationMs (Python's own
    # json.loads() accepts the bare "NaN"/"Infinity" tokens by default,
    # even though real JSON has no such literals) used to sail through
    # as "not negative" instead of being rejected.
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0:
        raise ContractValidationError("durationMs must be a finite, non-negative number")
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
    _require_iso_timestamp(payload, "date")
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
