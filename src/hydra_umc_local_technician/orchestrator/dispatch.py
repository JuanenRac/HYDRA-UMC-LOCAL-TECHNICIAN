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

This wires all 9 of the tools `policy.tool_matrix` declares: `storage.usage`,
`network.port_status`, `network.connectivity`, `system.temperature`,
`service.status`, `manifest.read`, `logs.read`, `process.list`,
`update.pending`.

`update.pending` is the one real HYDRA-UMC-UPDATER integration boundary:
it reuses that project's own already-tested GitHub discovery
(`github_client.fetch_all`), manifest parsing (`project_manifest.parse_manifest`)
and version comparison (`version_parse.Version`) instead of a second,
silently-drifting copy of any of it - the same "delegate to the real
logic elsewhere" principle `ecosystem_plan.py` already applies in
HYDRA-UMC-OS-REBUILDER. `hydra-umc-updater` is an OPTIONAL dependency
(the `update-check` extra) - imported lazily, guarded by `_HAS_UPDATE_CHECK`,
so every other tool in this package stays usable on a bare stdlib-only
install; `update.pending` itself degrades honestly (`available: false`)
when the extra is not installed, never a crash on import.

`logs.read` only ever opens exactly one real, allow-listed FILE
(`OrchestratorConfig.resolve_log_source`, never a directory or glob), and
every line it returns has already passed through
`knowledge.redaction.redact_lines()` before this function returns -
before the ToolResult is even assembled, not as a later serialization
step that a future change could accidentally skip.

`process.list` resolves a symbolic name to a real substring
(`OrchestratorConfig.resolve_process_pattern`) matched against real
`/proc/<pid>/cmdline` entries - never a raw, unfiltered process table
(this is the "which processes even count as relevant" design question
the module used to leave open: the answer is "only the ones an operator
explicitly allow-listed", the same symbolic-name discipline every other
handler here already uses). Honestly degrades with `available: false` on
a host with no real `/proc` (this dev machine included), the same
convention `system.temperature`/`service.status` already use.

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
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import __version__
from ..contracts import validate
from ..knowledge.redaction import redact_lines
from ..knowledge.trust import ToolRequest
from ..policy.tool_matrix import lookup_tool
from .allowlist import OrchestratorConfig, UnknownAllowlistEntry

# update.pending's own real integration boundary - see this module's own
# docstring above for why this is lazy/optional rather than a hard
# dependency of the whole package.
try:
    from hydra_umc_updater.github_client import fetch_all as _updater_fetch_all
    from hydra_umc_updater.project_manifest import ManifestValidationError as _UpdaterManifestValidationError
    from hydra_umc_updater.project_manifest import parse_manifest as _updater_parse_manifest
    from hydra_umc_updater.registry import entry_from_manifest as _updater_entry_from_manifest
    from hydra_umc_updater.version_parse import Version as _UpdaterVersion

    _HAS_UPDATE_CHECK = True
except ImportError:
    _HAS_UPDATE_CHECK = False
    # Real bug found while auditing CI: every actual call site below
    # already guards on _HAS_UPDATE_CHECK before touching these names,
    # but leaving them undefined here meant unittest.mock.patch.multiple
    # (used by UpdatePendingTests, without create=True) raised
    # AttributeError in any environment - including real CI - where the
    # optional hydra-umc-updater dependency isn't installed, even though
    # that test suite's own docstring promises it stays deterministic
    # and offline regardless of whether that extra is present.
    _updater_fetch_all = None
    _UpdaterManifestValidationError = None
    _updater_parse_manifest = None
    _updater_entry_from_manifest = None
    _UpdaterVersion = None


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


# The only real schemes _handle_network_connectivity will ever actually
# open - a real health endpoint is HTTP(S), never `data:`/`file:`/`ftp:`.
# Mirrors HYDRA-UMC-OPS-AGENT's own inventory.py check_http_health() -
# restricting this explicitly (rather than trying every scheme and hoping
# the result looks HTTP-shaped) is what stops a malformed/hostile URL
# from reaching urlopen() at all.
_SUPPORTED_HTTP_SCHEMES = ("http", "https")


def _handle_network_connectivity(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    # Distinct real check from network.port_status above: a real HTTP GET
    # against an allow-listed URL, reporting the endpoint's own real
    # status code - not just whether some process happens to be bound to
    # a port. See allowlist.py's own field comment for the full reasoning.
    name = arguments.get("name")
    if not isinstance(name, str) or not name:
        raise UnknownAllowlistEntry("network.connectivity requires a non-empty 'name' argument")
    url = config.resolve_connectivity_target(name)
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme not in _SUPPORTED_HTTP_SCHEMES:
        # A real, honest misconfiguration report - the allow-list itself
        # is fixed at construction time (see OrchestratorConfig's own
        # docstring), so reaching this means default_config() or a
        # caller's own config built an unsupported URL, not that
        # `arguments` smuggled one in.
        output = {"name": name, "url": url, "reachable": False, "status_code": None, "reason": f"unsupported URL scheme {scheme!r} - only http/https are ever checked"}
        return output, f"rejected {url!r} before ever calling urlopen() - unsupported scheme"
    timeout_s = 3.0
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as response:  # noqa: S310 - scheme already restricted above
            status_code = response.getcode()
        output = {"name": name, "url": url, "reachable": True, "status_code": status_code, "reason": None}
        return output, f"urlopen({url!r}, timeout={timeout_s}) -> HTTP {status_code}"
    except urllib.error.HTTPError as exc:
        # A real HTTP error response (4xx/5xx) still means the endpoint
        # itself answered - genuinely different from a connection that
        # never got a response at all (URLError below).
        output = {"name": name, "url": url, "reachable": True, "status_code": exc.code, "reason": f"HTTP {exc.code}"}
        return output, f"urlopen({url!r}, timeout={timeout_s}) -> HTTP {exc.code} (endpoint answered, with an error status)"
    except urllib.error.URLError as exc:
        output = {"name": name, "url": url, "reachable": False, "status_code": None, "reason": str(exc.reason)}
        return output, f"urlopen({url!r}, timeout={timeout_s}) failed: {exc.reason}"


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


# Fase 3's own real bound on logs.read, not a stylistic default: a large
# request never reads an unbounded slice of a real log file, and the
# tail itself is bounded in raw BYTES first (before ever splitting into
# lines) so a request against a log that has grown large still costs a
# fixed amount of memory rather than scaling with the file's own size.
_LOGS_READ_DEFAULT_LINES = 50
_LOGS_READ_MAX_LINES = 500
_LOGS_READ_MAX_TAIL_BYTES = 1_000_000


def _tail_lines(path: Path, max_lines: int) -> list[str]:
    """The last `max_lines` lines of `path`, reading at most
    `_LOGS_READ_MAX_TAIL_BYTES` of its own tail regardless of how many
    lines that produces. When the read window starts mid-file, the FIRST
    decoded line is dropped - it is very likely a partial line split at
    an arbitrary byte offset, and a truncated line silently presented as
    complete would be worse than one fewer real line."""
    size = path.stat().st_size
    read_from = max(0, size - _LOGS_READ_MAX_TAIL_BYTES)
    with path.open("rb") as f:
        f.seek(read_from)
        raw = f.read()
    lines = raw.decode("utf-8", errors="replace").splitlines()
    if read_from > 0 and lines:
        lines = lines[1:]
    return lines[-max_lines:] if max_lines > 0 else []


def _handle_logs_read(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    name = arguments.get("name")
    if not isinstance(name, str) or not name:
        raise UnknownAllowlistEntry("logs.read requires a non-empty 'name' argument")
    path = config.resolve_log_source(name)
    requested = arguments.get("lines", _LOGS_READ_DEFAULT_LINES)
    if not isinstance(requested, int) or requested <= 0:
        requested = _LOGS_READ_DEFAULT_LINES
    max_lines = min(requested, _LOGS_READ_MAX_LINES)
    if not path.is_file():
        # A real, expected state (a service that has not logged anything
        # yet, or a log source configured ahead of the file existing) -
        # never a ToolDispatchError, which is reserved for a request that
        # cannot be routed at all.
        output = {"name": name, "path": str(path), "exists": False, "lines": [], "returned": 0}
        return output, f"{path} does not exist - nothing to read yet"
    raw_lines = _tail_lines(path, max_lines)
    redacted = redact_lines(raw_lines)
    output = {"name": name, "path": str(path), "exists": True, "lines": redacted, "returned": len(redacted)}
    return output, f"read the last {len(redacted)} line(s) of {path} (redacted via knowledge.redaction before leaving this module)"


# process.list's own real bound: never report more than this many real
# matches for one pattern - an allow-listed ecosystem process is expected
# to have a handful of instances at most (one per camera, say), never an
# unbounded count; a pattern that somehow matches more says something is
# already wrong and is itself worth surfacing via `truncated`.
_PROCESS_LIST_MAX_MATCHES = 20


def _list_proc_matches(pattern: str) -> tuple[list[dict[str, Any]], bool]:
    """Real, read-only /proc enumeration - the same mechanism `ps` itself
    is built on, with no subprocess spawned. Each match is a real PID
    whose real cmdline (as the kernel itself reports it, never the
    process's own possibly-spoofed argv[0] alone) contains `pattern`. A
    PID that exits between `iterdir()` and reading its own `cmdline` is a
    real, benign race (the process is simply no longer there) - skipped,
    never an error. Returns (matches, truncated)."""
    matches: list[dict[str, Any]] = []
    truncated = False
    proc_dir = Path("/proc")
    for entry in sorted(proc_dir.iterdir(), key=lambda p: p.name):
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        cmdline = raw.decode("utf-8", errors="replace").replace("\x00", " ").strip()
        if pattern not in cmdline:
            continue
        if len(matches) >= _PROCESS_LIST_MAX_MATCHES:
            truncated = True
            break
        matches.append({"pid": int(entry.name), "cmdline": cmdline})
    return matches, truncated


def _handle_process_list(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    name = arguments.get("name")
    if not isinstance(name, str) or not name:
        raise UnknownAllowlistEntry("process.list requires a non-empty 'name' argument")
    pattern = config.resolve_process_pattern(name)
    if not Path("/proc").is_dir():
        # Honest platform degradation, same convention as
        # system.temperature/service.status - never a guessed or empty-
        # by-omission result on a host with no real /proc (this dev
        # machine included).
        output = {"name": name, "available": False, "reason": "no /proc on this platform", "running": None, "matches": []}
        return output, "process.list needs a real Linux host with /proc - not available here"
    matches, truncated = _list_proc_matches(pattern)
    output = {
        "name": name,
        "available": True,
        "running": len(matches) > 0,
        "matches": matches,
        "truncated": truncated,
    }
    return output, f"{len(matches)} real process(es) matching pattern {pattern!r} under /proc" + (" (truncated)" if truncated else "")


def _handle_update_pending(config: OrchestratorConfig, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    project = arguments.get("project")
    if not isinstance(project, str) or not project:
        raise UnknownAllowlistEntry("update.pending requires a non-empty 'project' argument")
    # Reuses manifest.read's own real allow-list boundary (PROJECT_NAME_PATTERN
    # + "must resolve as a direct child of ecosystem_root") rather than a
    # second one - update.pending never needs a target beyond that same
    # local manifest file.
    manifest_path = config.resolve_project_manifest_path(project)

    if not _HAS_UPDATE_CHECK:
        output = {
            "project": project, "available": False,
            "reason": "hydra-umc-updater is not installed - install this package with its optional 'update-check' extra",
            "pending": None,
        }
        return output, "update.pending needs the optional hydra-umc-updater dependency, which is not installed"

    try:
        raw = manifest_path.read_text(encoding="utf-8")
        manifest = _updater_parse_manifest(raw, expected_name=project)
    except (OSError, _UpdaterManifestValidationError) as exc:
        output = {"project": project, "available": True, "found": False, "reason": str(exc), "pending": None}
        return output, f"could not read/parse {manifest_path}: {exc}"

    entry = _updater_entry_from_manifest(manifest)
    local_major, local_minor, local_patch = (int(part) for part in manifest.version.split("."))
    local_version = _UpdaterVersion(local_major, local_minor, local_patch)

    remote_results = _updater_fetch_all([entry])
    remote_status = remote_results.get(entry.name)
    if remote_status is None or remote_status.version is None:
        reason = remote_status.error if remote_status is not None else "no result returned from GitHub"
        output = {
            "project": project, "available": True, "found": True,
            "local_version": str(local_version), "remote_version": None,
            "pending": None, "reason": reason,
        }
        return output, f"could not determine {project}'s real GitHub version: {reason}"

    pending = local_version < remote_status.version
    output = {
        "project": project, "available": True, "found": True,
        "local_version": str(local_version), "remote_version": str(remote_status.version),
        "pending": pending, "reason": None,
    }
    verdict = "update pending" if pending else ("ahead of GitHub" if remote_status.version < local_version else "up to date")
    return output, f"{project}: local {local_version}, GitHub {remote_status.version} - {verdict}"


# tool name -> handler(config, arguments) -> (output, evidence). Every
# entry here MUST have implemented=True in policy.tool_matrix.TOOL_MATRIX -
# tested by test_dispatch.py's own test_every_implemented_tool_has_a_handler
# (and vice versa), so the two can never silently drift apart.
_HANDLERS = {
    "storage.usage": _handle_storage_usage,
    "network.port_status": _handle_network_port_status,
    "network.connectivity": _handle_network_connectivity,
    "system.temperature": _handle_system_temperature,
    "service.status": _handle_service_status,
    "manifest.read": _handle_manifest_read,
    "logs.read": _handle_logs_read,
    "process.list": _handle_process_list,
    "update.pending": _handle_update_pending,
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
