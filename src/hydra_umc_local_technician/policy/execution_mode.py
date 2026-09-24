# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/policy/execution_mode.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Diagnosis-only by default, and what it takes to leave that mode.

Every tool this technician runs is read-only. This module states the rule
in one place so it cannot be relaxed by accident: `DIAGNOSIS_ONLY` refuses
any action above OBSERVE, always. `ASSISTED` still refuses an action
above OBSERVE unless a human approval record accompanies it, the record
names exactly that action, and its signature has been verified by the
caller against a policy the operator controls. Model text never appears
in this decision: only the mode, the requested level and the record.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .risk_levels import RiskLevel


class ExecutionMode(str, Enum):
    DIAGNOSIS_ONLY = "diagnosis_only"
    ASSISTED = "assisted"


DEFAULT_MODE = ExecutionMode.DIAGNOSIS_ONLY


@dataclass(frozen=True)
class ApprovalRecord:
    """A human's approval of one specific action.

    `signature_verified` is set by the code that checked the signature
    against the operator's policy; this module never verifies signatures
    itself and never treats an unverified record as an approval.
    """

    approved_by: str
    action: str
    signature_verified: bool


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


def decide(mode: ExecutionMode, level: RiskLevel, action: str, approval: ApprovalRecord | None = None) -> Decision:
    """Whether `action` at `level` may run in `mode` with `approval`."""
    if level <= RiskLevel.OBSERVE:
        return Decision(True, "read-only action")
    if mode is ExecutionMode.DIAGNOSIS_ONLY:
        return Decision(False, f"{action!r} is {level.wire_name}: diagnosis-only mode refuses every action above observe")
    if approval is None:
        return Decision(False, f"{action!r} needs a recorded human approval")
    if not approval.approved_by.strip():
        return Decision(False, "the approval names nobody")
    if approval.action != action:
        return Decision(False, f"the approval is for {approval.action!r}, not {action!r}")
    if not approval.signature_verified:
        return Decision(False, "the approval's signature was not verified against the operator's policy")
    return Decision(True, f"approved by {approval.approved_by}")
