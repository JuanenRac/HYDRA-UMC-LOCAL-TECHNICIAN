# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/orchestrator/dispatch.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 3: deterministic code wiring the first real OBSERVE-level tool
handlers to `policy.tool_matrix`, with policy enforcement on every call.

`dispatch_tool_request()` is the ONE place a `ToolRequest` ever becomes a
real read against this host - re-checking `policy.tool_matrix.lookup_tool()`
independently rather than trusting that `knowledge.trust.build_tool_request_from_model_output()`
already did (defense in depth: a `ToolRequest` could in principle reach
this function some other way, e.g. deserialized from a stored
`EvidenceBundle`, and this function must never assume its caller already
enforced policy). Every handler below is OBSERVE level and read-only by
construction - none accepts a raw path/host/port from `arguments`, only a
short symbolic name resolved through `allowlist.OrchestratorConfig` (see
that module's own header comment for why).

This first slice wires 5 of the 9 tools `policy.tool_matrix` declares:
`storage.usage`, `network.port_status`, `system.temperature`,
`service.status`, `manifest.read`. The other 4 (`process.list`,
`network.connectivity`, `update.pending`, `logs.read`) stay
`implemented=False` - real, deliberate scope for a later slice, not an
oversight (`process.list`/`logs.read` need their own filtering/redaction
design beyond what a symbolic-name allow-list alone would cover;
`update.pending` needs a real HYDRA-UMC-UPDATER integration boundary;
`network.connectivity` is the same shape as `network.port_status` but
against a REMOTE allow-listed endpoint, worth its own review rather than
riding along here unverified).

Real platform honesty, not a simulated pass: `system.temperature` and
`service.status` degrade with a distinct, typed reason (never a guessed
reading) on a host without the real Linux sensor/`systemctl` - the same
pattern HYDRA-UMC-OPS-AGENT's own inventory.py already uses for exactly
this reason.
"""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

from .. import __version__
from ..contracts import validate
from ..knowledge.trust import ToolRequest
from ..policy.tool_matrix import lookup_tool
from .allowlist import OrchestratorConfig, UnknownAllowlistEntry


class ToolDispatchError(Exception):
    """Raised when a request cannot even be routed to a handler at all
    (unknown/unimplemented tool) - distinct from a real handler running
    and reporting its own failure, which becomes a `status: "error"`
    ToolResult instead (see dispatch_tool_request's own return, never an
    exception for that case)."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tool_result(
    request_id: str,
    status: str,
    output: dict[str, Any],
    evidence: str,
    started_at: float,
    error_code: str | None = None,
) -> dict[str, Any]:
    payload = {
        "requestId": request_id,
        "status": status,
        "output": output,
        "evidence": evidence,
        "timestamp": _now_iso(),
        "durationMs": max(0.0, (time.monotonic() - started_at) * 1000.0),
        "toolVersion": __version__,
        "errorCode": error_code,
    }
    # A ToolResult this module itself cannot construct validly is a real
    # bug in this dispatcher, not a case to smuggle out silently - let it
    # raise ContractValidationError rather than returning a payload no
    # consumer downstream could trust either.
    validate("ToolResult", payload)
    return payload


def _handle_storage_usage(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    name = arguments.get("name")
    if not isinstance(name, str) or not name:
        raise UnknownAllowlistEntry("storage.usage requires a non-empty 'name' argument")
    path = config.resolve_storage_path(name)
    usage = shutil.disk_usage(path)
    output = {
        "name": name,
        "path": str(path),
        "totalBytes": usage.total,
        "usedBytes": usage.used,
        "freeBytes": usage.free,
    }
    return output, f"disk_usage({path}) via shutil.disk_usage"


def _handle_network_port_status(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    name = arguments.get("name")
    if not isinstance(name, str) or not name:
        raise UnknownAllowlistEntry("network.port_status requires a non-empty 'name' argument")
    host, port = config.resolve_port(name)
    timeout_s = 2.0
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            listening = True
        detail = f"connected to {host}:{port}"
    except OSError as exc:
        listening = False
        detail = f"could not connect to {host}:{port}: {exc}"
    output = {"name": name, "host": host, "port": port, "listening": listening}
    return output, f"socket.create_connection(({host!r}, {port}), timeout={timeout_s}): {detail}"


def _handle_system_temperature(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    # Same real Linux thermal-zone path HYDRA-UMC-SERVER's own
    # getSystemMetrics() reads (see policy.tool_matrix's own docstring for
    # this tool) - millidegrees Celsius as a plain integer text file. No
    # fallback to a guessed value on any other platform or if the sensor
    # is simply absent; report the real, honest reason instead.
    thermal_path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(thermal_path, encoding="ascii") as handle:
            raw = handle.read().strip()
        millidegrees = int(raw)
    except (OSError, ValueError) as exc:
        output = {"available": False, "reason": f"{thermal_path} unavailable: {exc}"}
        return output, f"open({thermal_path!r}) failed - honest degradation, no guessed reading"
    output = {"available": True, "celsius": millidegrees / 1000.0}
    return output, f"read {thermal_path}"


def _handle_service_status(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    name = arguments.get("name")
    if not isinstance(name, str) or not name:
        raise UnknownAllowlistEntry("service.status requires a non-empty 'name' argument")
    unit = config.resolve_systemd_unit(name)
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        # HYDRA-UMC-OPS-AGENT's own honest systemd-unavailable degradation
        # pattern (inventory.py's own SystemdUnavailableError) - a
        # non-Linux dev machine, or a Linux host without systemd, reports
        # this as itself, never a guessed "inactive".
        output = {"unit": unit, "active": False, "available": False, "reason": "systemctl not found on PATH - not a real systemd host"}
        return output, "shutil.which('systemctl') returned None - honest degradation, no guessed status"
    result = subprocess.run(
        [systemctl, "is-active", unit],
        capture_output=True, text=True, timeout=5.0, check=False,
    )
    detail = (result.stdout or result.stderr or "").strip() or f"exit code {result.returncode}"
    output = {"unit": unit, "active": result.returncode == 0, "available": True, "reason": detail}
    return output, f"systemctl is-active {unit}: {detail}"


def _handle_manifest_read(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    project = arguments.get("project")
    if not isinstance(project, str) or not project:
        raise UnknownAllowlistEntry("manifest.read requires a non-empty 'project' argument")
    manifest_path = config.resolve_project_manifest_path(project)
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        output = {"project": project, "found": False, "reason": str(exc)}
        return output, f"read {manifest_path}: failed ({exc})"
    if not isinstance(manifest, dict):
        output = {"project": project, "found": False, "reason": "manifest is not a JSON object"}
        return output, f"read {manifest_path}: not a JSON object"
    output = {
        "project": project,
        "found": True,
        "name": manifest.get("name"),
        "version": manifest.get("version"),
        "maturity": manifest.get("maturity"),
        "role": manifest.get("role"),
    }
    return output, f"read {manifest_path}"


# tool name -> handler(config, arguments) -> (output, evidence). Every
# entry here MUST have implemented=True in policy.tool_matrix.TOOL_MATRIX -
# tested by test_dispatch.py's own test_every_implemented_tool_has_a_handler
# (and vice versa), so the two can never silently drift apart.
_HANDLERS = {
    "storage.usage": _handle_storage_usage,
    "network.port_status": _handle_network_port_status,
    "system.temperature": _handle_system_temperature,
    "service.status": _handle_service_status,
    "manifest.read": _handle_manifest_read,
}


def dispatch_tool_request(request: ToolRequest, config: OrchestratorConfig) -> dict[str, Any]:
    """Runs `request` for real and returns a validated ToolResult payload
    (a dict already matching contracts.py's own ToolResult shape - never
    an internal type the caller would need to know how to serialize).

    Never raises for a tool that IS implemented and simply fails at
    runtime (a missing sensor, an unreachable port, a systemd-less host,
    a malformed manifest) - those become a real `status: "error"`
    ToolResult with a `reason` in `output`, since that failure is itself
    genuine diagnostic evidence. Raises ToolDispatchError only when the
    request can't be routed at all: an unregistered tool, one that is
    registered but not implemented (redundant with
    `build_tool_request_from_model_output()`'s own refusal, but this
    function must not assume every caller went through that path first),
    or an argument that fails the allow-list (`UnknownAllowlistEntry`,
    re-raised as `ToolDispatchError` so this module has one exception
    type its own caller needs to catch).
    """
    started_at = time.monotonic()
    descriptor = lookup_tool(request.tool)
    if descriptor is None:
        raise ToolDispatchError(f"'{request.tool}' is not a registered tool")
    if not descriptor.implemented:
        raise ToolDispatchError(f"'{request.tool}' is registered but not implemented")
    handler = _HANDLERS.get(request.tool)
    if handler is None:
        # descriptor.implemented=True but no handler wired here would be a
        # real bug in this module (see _HANDLERS' own comment) - refusing
        # rather than pretending is still the honest response.
        raise ToolDispatchError(f"'{request.tool}' is marked implemented but has no real handler wired")

    try:
        output, evidence = handler(config, request.arguments)
    except UnknownAllowlistEntry as exc:
        raise ToolDispatchError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - a real, unexpected handler failure is genuine evidence, not a crash
        return _tool_result(
            request.request_id, "error", {"reason": str(exc)}, f"{request.tool} raised {type(exc).__name__}: {exc}",
            started_at, error_code=type(exc).__name__,
        )
    return _tool_result(request.request_id, "ok", output, evidence, started_at)
