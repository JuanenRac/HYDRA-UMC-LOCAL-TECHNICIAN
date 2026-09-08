# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/policy/risk_levels.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The six risk levels this technician defines - the single
non-negotiable principle behind all of them: the AI never gets authority
by generating a response. Policy, permissions, interlocks and human
confirmation decide every action, never model text.

Levels 5 (PHYSICAL_ACTION) and 4 (PRIVILEGED_CHANGE) are declared here for
completeness of the contract, but nothing in this codebase implements
either - Fase 0's own scope is strictly INFORM through REVERSIBLE_OPERATION,
and even REVERSIBLE_OPERATION is not yet wired to a real tool (see
tool_matrix.py's own header comment).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class RiskLevel(IntEnum):
    """Ordered so a numeric comparison (e.g. `level <= RiskLevel.OBSERVE`)
    is meaningful - a higher value is always a higher-risk action."""
    INFORM = 0
    OBSERVE = 1
    PREPARE = 2
    REVERSIBLE_OPERATION = 3
    PRIVILEGED_CHANGE = 4
    PHYSICAL_ACTION = 5

    @property
    def wire_name(self) -> str:
        """The exact lowercase string this level is serialized as in every
        real contract (contracts/*.schema.json's own `riskLevel`/`risk`
        enum) - kept as one explicit mapping so the wire format never
        silently drifts from Python's own enum member spelling."""
        return _WIRE_NAMES[self]

    @staticmethod
    def from_wire_name(name: str) -> "RiskLevel":
        for level, wire_name in _WIRE_NAMES.items():
            if wire_name == name:
                return level
        raise ValueError(f"unknown risk level: {name!r}")


_WIRE_NAMES: dict[RiskLevel, str] = {
    RiskLevel.INFORM: "inform",
    RiskLevel.OBSERVE: "observe",
    RiskLevel.PREPARE: "prepare",
    RiskLevel.REVERSIBLE_OPERATION: "reversible_operation",
    RiskLevel.PRIVILEGED_CHANGE: "privileged_change",
    RiskLevel.PHYSICAL_ACTION: "physical_action",
}


@dataclass(frozen=True)
class RiskLevelPolicy:
    """What a given level is allowed to do - see docs/SECURITY_MODEL.md
    for the full model this mirrors."""
    level: RiskLevel
    can_read_tools: bool
    can_mutate: bool
    requires_confirmation: bool
    implemented: bool
    description: str


# Fase 0 declares all six levels' real policy - it does not implement a
# tool at REVERSIBLE_OPERATION or above (implemented=False there), and
# PRIVILEGED_CHANGE/PHYSICAL_ACTION are explicitly out of scope for this
# entire technician until a future phase with its own separate design,
# authorization and (for PHYSICAL_ACTION) real interlocks exists.
POLICIES: dict[RiskLevel, RiskLevelPolicy] = {
    RiskLevel.INFORM: RiskLevelPolicy(
        level=RiskLevel.INFORM,
        can_read_tools=False,
        can_mutate=False,
        requires_confirmation=False,
        implemented=True,
        description="Read documentation or explain status. No tool access at all.",
    ),
    RiskLevel.OBSERVE: RiskLevelPolicy(
        level=RiskLevel.OBSERVE,
        can_read_tools=True,
        can_mutate=False,
        requires_confirmation=False,
        implemented=True,
        description="Read manifests, versions, allowed logs, service health, storage, temperature and connectivity. Never modifies anything.",
    ),
    RiskLevel.PREPARE: RiskLevelPolicy(
        level=RiskLevel.PREPARE,
        can_read_tools=True,
        can_mutate=False,
        requires_confirmation=True,
        implemented=True,
        description="Generate a diagnosis, plan, proposed diff, evidence bundle or un-executed command. Must show the proposal to the user before anything else happens.",
    ),
    RiskLevel.REVERSIBLE_OPERATION: RiskLevelPolicy(
        level=RiskLevel.REVERSIBLE_OPERATION,
        can_read_tools=True,
        can_mutate=True,
        requires_confirmation=True,
        implemented=False,
        description="Restart an authorized service, rotate a log, refresh an index, or download (never apply) an update. Requires authenticated confirmation, a pre-check, a post-check and a durable record.",
    ),
    RiskLevel.PRIVILEGED_CHANGE: RiskLevelPolicy(
        level=RiskLevel.PRIVILEGED_CHANGE,
        can_read_tools=True,
        can_mutate=True,
        requires_confirmation=True,
        implemented=False,
        description="Install or apply a package, change configuration or credentials. Requires an administrator role, a second confirmation, a backup/rollback and a maintenance window. Will not be implemented at the start.",
    ),
    RiskLevel.PHYSICAL_ACTION: RiskLevelPolicy(
        level=RiskLevel.PHYSICAL_ACTION,
        can_read_tools=False,
        can_mutate=True,
        requires_confirmation=True,
        implemented=False,
        description="Motion, power, actuators, firmware or safety. Forbidden for this AI until a dedicated design, separate authorization, E-stop, interlocks and physical validation exist. Never an automatic consequence of anything.",
    ),
}
