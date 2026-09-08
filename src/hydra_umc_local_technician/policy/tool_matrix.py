# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/policy/tool_matrix.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 0's own real deliverable: the tool/risk-level matrix. This is a
declarative registry of every tool THIS TECHNICIAN WILL EVER BE ALLOWED
TO CALL and its fixed risk level - not an implementation of any tool. A
future orchestrator (a later phase) looks a tool name up here before
ever considering a model's request to call it; a name that is not in
this dict cannot be called, full stop - there is no "call anything and
let the risk level be decided later" path.

Every entry listed here is OBSERVE level - what this technician may read
in its first version (service health, processes, ports, storage,
temperature, connectivity, pending updates, permitted logs). No tool at
REVERSIBLE_OPERATION or above is registered yet - see risk_levels.py's
own POLICIES for why (Fase 0 does not implement one).
"""
from __future__ import annotations

from dataclasses import dataclass

from .risk_levels import RiskLevel


@dataclass(frozen=True)
class ToolDescriptor:
    """One real, allowed tool - name, fixed risk level, and a short
    description of exactly what it may read. `implemented=False` means
    this tool is declared (so a future ToolRequest naming it is
    recognized as legitimate) but has no real handler yet - calling it
    today must fail closed, not silently no-op."""
    name: str
    risk_level: RiskLevel
    description: str
    implemented: bool = False


# Diagnostics for services, processes, ports, storage, temperature,
# connectivity, updates, logs and application health. Naming convention:
# "<area>.<verb>", matching contracts/tool_request.schema.json's own
# `tool` field shape.
TOOL_MATRIX: dict[str, ToolDescriptor] = {
    "service.status": ToolDescriptor(
        name="service.status",
        risk_level=RiskLevel.OBSERVE,
        description="Reports whether a named systemd unit is active, matching HYDRA-UMC-OPS-AGENT's own honest systemd-unavailable degradation pattern.",
    ),
    "process.list": ToolDescriptor(
        name="process.list",
        risk_level=RiskLevel.OBSERVE,
        description="Lists running processes relevant to the ecosystem's own services - never a raw, unfiltered process table.",
    ),
    "network.port_status": ToolDescriptor(
        name="network.port_status",
        risk_level=RiskLevel.OBSERVE,
        description="Reports whether an expected local port is listening.",
    ),
    "storage.usage": ToolDescriptor(
        name="storage.usage",
        risk_level=RiskLevel.OBSERVE,
        description="Reports disk usage for the paths this ecosystem's own services actually write to.",
    ),
    "system.temperature": ToolDescriptor(
        name="system.temperature",
        risk_level=RiskLevel.OBSERVE,
        description="Reports the real CPU/board temperature, honestly degrading (never a guessed value) where the sensor isn't available - same convention as HYDRA-UMC-SERVER's own getSystemMetrics().",
    ),
    "network.connectivity": ToolDescriptor(
        name="network.connectivity",
        risk_level=RiskLevel.OBSERVE,
        description="Reports reachability of a configured, allow-listed local endpoint - never an arbitrary caller-supplied host.",
    ),
    "update.pending": ToolDescriptor(
        name="update.pending",
        risk_level=RiskLevel.OBSERVE,
        description="Reports whether HYDRA-UMC-UPDATER has a pending update for a named project - never downloads or applies one itself.",
    ),
    "logs.read": ToolDescriptor(
        name="logs.read",
        risk_level=RiskLevel.OBSERVE,
        description="Reads a bounded window of an allow-listed log source, always through knowledge/redaction.py before the result ever leaves this module.",
    ),
    "manifest.read": ToolDescriptor(
        name="manifest.read",
        risk_level=RiskLevel.OBSERVE,
        description="Reads a real hydra-umc.project.json (name/version/maturity/role) for a named project - same real, tested pattern as HYDRA-UMC-OPS-AGENT's and HYDRA-UMC-DEV-SERVER's own inventory.py.",
    ),
}


def lookup_tool(name: str) -> ToolDescriptor | None:
    """Returns the real, registered descriptor for `name`, or None if it
    is not a recognized tool at all - the orchestrator's own future
    dispatch must treat None as an automatic, unconditional refusal, not
    a case to guess a default risk level for."""
    return TOOL_MATRIX.get(name)
