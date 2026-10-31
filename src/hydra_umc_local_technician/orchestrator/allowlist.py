# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/orchestrator/allowlist.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What an OBSERVE-level tool is actually allowed to look at.

`policy.tool_matrix`'s own descriptions are explicit that these tools read
a bounded, known set of things - "the paths this ecosystem's own services
actually write to", "an expected local port", never an arbitrary
caller-supplied target. A `ToolRequest.arguments` dict is data that
ultimately traces back to a model's own output (see `knowledge/trust.py`'s
own header comment on why that boundary matters) - so every handler in
`dispatch.py` takes a short, allow-listed SYMBOLIC NAME as its argument
(`"server_data"`, `"server_http"`, a real ecosystem project name already
constrained to `PROJECT_NAME_PATTERN`), resolved here against a fixed
`OrchestratorConfig`, never a raw path/host/port a caller supplies
directly. A name this config doesn't recognize is refused before any
filesystem or network access happens at all - the same "unknown name is
an automatic refusal, not a guess" principle `policy.tool_matrix.lookup_tool()`
already applies to tool names themselves.
"""
from __future__ import annotations

import re
from typing import Any
from dataclasses import dataclass, field
from pathlib import Path

from ..policy.execution_mode import DEFAULT_MODE, ExecutionMode


class UnknownAllowlistEntry(ValueError):
    """Raised for a symbolic name this config does not recognize - a real,
    named refusal, never a guessed default target."""


# Mirrors HYDRA-UMC-SDK's own PROJECT_NAME_PATTERN
# (clients/python/src/hydra_umc_sdk/validation.py) - every real
# hydra-umc.project.json this ecosystem publishes names itself this way.
PROJECT_NAME_PATTERN = re.compile(r"^(HYDRA-UMC|URTC)(-[A-Z0-9-]+)?$")


@dataclass(frozen=True)
class OrchestratorConfig:
    """The one real, fixed set of things this technician's OBSERVE tools
    may ever touch on a given host. `default_config()` below gives the
    real, documented defaults for a standard CM5 install; a caller
    (production wiring, or a test) may build a different one explicitly -
    there is deliberately no way to add an entry from inside a tool call
    itself.
    """

    # symbolic name -> real filesystem path `storage.usage` may report on.
    storage_paths: dict[str, Path] = field(default_factory=dict)
    # symbolic name -> (host, port) `network.port_status` may probe.
    ports: dict[str, tuple[str, int]] = field(default_factory=dict)
    # symbolic name -> a real, fixed http(s) URL `network.connectivity`
    # may GET - a separate namespace and a separate real check from
    # `ports` on purpose: `port_status` is a bare TCP connect ("is
    # something listening"), `connectivity` is a real HTTP GET reporting
    # the endpoint's own real status code ("is it actually answering
    # requests, and how") - the same real distinction
    # HYDRA-UMC-OPS-AGENT's own inventory.py already draws between
    # `check_systemd_unit_health()` and `check_http_health()`.
    connectivity_targets: dict[str, str] = field(default_factory=dict)
    # real systemd unit names `service.status` may query - not a pattern,
    # an exact allow-list, since a unit name reaches a real subprocess
    # argument.
    systemd_units: tuple[str, ...] = ()
    # the one real directory `manifest.read` scans - a project name is
    # still validated against PROJECT_NAME_PATTERN AND checked to resolve
    # to a direct child of this root (see resolve_project_manifest_path
    # below), so this alone is not the only guard.
    ecosystem_root: Path | None = None
    # symbolic name -> a real, fixed log FILE `logs.read` may open - never
    # a directory or glob (a caller only ever gets bytes from exactly the
    # one file an operator already decided is safe to expose), and always
    # piped through knowledge.redaction.redact_lines() before leaving
    # dispatch.py, regardless of what this dict itself points at.
    log_sources: dict[str, Path] = field(default_factory=dict)
    # symbolic name -> a real substring `process.list` matches against a
    # real process's own /proc/<pid>/cmdline - never a raw, unfiltered
    # process table (policy.tool_matrix's own description of this tool),
    # and never a pattern a caller supplies directly: only ever one an
    # operator already put here for exactly this purpose.
    process_patterns: dict[str, str] = field(default_factory=dict)
    # What this technician may do at all (policy/execution_mode.py). Every tool registered today is read-only, so the
    # default, diagnosis-only, refuses nothing that exists; it stands in front of any tool added later above OBSERVE.
    execution_mode: ExecutionMode = DEFAULT_MODE
    # symbolic name -> a real, fixed directory `knowledge.search` (Fase 1)
    # may index - never a raw path a caller supplies, and never "the
    # whole disk": an operator decides up front exactly which real
    # documentation/manifest/contract trees this technician is allowed to
    # read at all. See knowledge/index.py's own further, per-file bounds
    # (allowed suffixes, size cap, file-count cap) - this allow-list is
    # the outer boundary, not the only one.
    knowledge_sources: dict[str, Path] = field(default_factory=dict)
    # the append-only audit journal of every tool request (orchestrator/audit.py), or None when the deployment
    # did not turn it on. When it is set, a request whose first line cannot be written is not run.
    audit_log: Any = None
    # Two optional tools are CLOSED by default and open only when the operator turns their switch on in the
    # configuration file (`"tools": {"journalRead": {"enabled": true, "units": [...]}, "serverMetrics": {"enabled":
    # true, "targets": {...}}}`): `journal.read` (the systemd journal of an allow-listed unit) and `server.metrics`
    # (the Prometheus text of an allow-listed endpoint). Closed means the call is refused before anything is read.
    journal_read_enabled: bool = False
    # exact systemd unit names `journal.read` may read - an exact allow-list, as for `systemd_units`.
    journal_units: tuple[str, ...] = ()
    server_metrics_enabled: bool = False
    # symbolic name -> a fixed http(s) URL of a metrics endpoint `server.metrics` may GET.
    metrics_targets: dict[str, str] = field(default_factory=dict)

    def resolve_storage_path(self, name: str) -> Path:
        try:
            return self.storage_paths[name]
        except KeyError:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed storage path") from None

    def resolve_port(self, name: str) -> tuple[str, int]:
        try:
            return self.ports[name]
        except KeyError:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed port") from None

    def resolve_connectivity_target(self, name: str) -> str:
        try:
            return self.connectivity_targets[name]
        except KeyError:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed connectivity target") from None

    def resolve_systemd_unit(self, name: str) -> str:
        if name not in self.systemd_units:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed systemd unit")
        return name

    def resolve_journal_unit(self, name: str) -> str:
        if not self.journal_read_enabled:
            raise UnknownAllowlistEntry("journal.read is switched off in the configuration")
        if name not in self.journal_units:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed journal unit")
        return name

    def resolve_metrics_target(self, name: str) -> str:
        if not self.server_metrics_enabled:
            raise UnknownAllowlistEntry("server.metrics is switched off in the configuration")
        try:
            return self.metrics_targets[name]
        except KeyError:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed metrics target") from None

    def resolve_log_source(self, name: str) -> Path:
        try:
            return self.log_sources[name]
        except KeyError:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed log source") from None

    def resolve_process_pattern(self, name: str) -> str:
        try:
            return self.process_patterns[name]
        except KeyError:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed process pattern") from None

    def resolve_knowledge_source(self, name: str) -> Path:
        try:
            return self.knowledge_sources[name]
        except KeyError:
            raise UnknownAllowlistEntry(f"'{name}' is not an allow-listed knowledge source") from None

    def resolve_project_manifest_path(self, project: str) -> Path:
        """Real path-traversal defense in depth: PROJECT_NAME_PATTERN
        alone already rejects a `/`, `..`, or any character outside
        `[A-Z0-9-]`, but this also confirms the resolved path stays below
        `ecosystem_root` (never a symlink escape) before ever returning it."""
        if self.ecosystem_root is None:
            raise UnknownAllowlistEntry("no ecosystem_root configured - manifest.read is unavailable")
        if not PROJECT_NAME_PATTERN.fullmatch(project):
            raise UnknownAllowlistEntry(f"{project!r} is not a real HYDRA-UMC/URTC project name")
        # URTC repositories describe themselves in urtc.project.json
        manifest_name = "urtc.project.json" if project.startswith("URTC") else "hydra-umc.project.json"
        candidate = (self.ecosystem_root / project / manifest_name).resolve()
        root = self.ecosystem_root.resolve()
        if root not in candidate.parents:
            raise UnknownAllowlistEntry(f"{project!r} does not resolve under the configured ecosystem root")
        return candidate


def default_config(ecosystem_root: Path | None = None) -> OrchestratorConfig:
    """The real, documented defaults for a standard install - HYDRA-UMC-SERVER's
    own local HTTP port (3000, see HYDRA-UMC-SERVER's own README) and data
    directory, and the systemd units HYDRA-UMC-OS's own provisioning
    scripts install. `ecosystem_root` defaults to None (manifest.read
    unavailable) rather than guessing a real filesystem layout that may
    not exist on this host - production wiring passes the real one
    explicitly.
    """
    return OrchestratorConfig(
        storage_paths={
            "server_data": Path("/opt/hydra-umc/server/data"),
        },
        ports={
            "server_http": ("127.0.0.1", 3000),
        },
        connectivity_targets={
            "server_hydra_info": "http://127.0.0.1:3000/api/hydra-info",
        },
        systemd_units=(
            "hydra-umc-server",
        ),
        ecosystem_root=ecosystem_root,
        log_sources={
            # HYDRA-UMC-SERVER's own real LOG_FILE constant (src/server.ts):
            # path.join(process.cwd(), "data", "logs", "server.log") - its
            # real installed cwd on the CM5 is /opt/hydra-umc/server.
            "server_log": Path("/opt/hydra-umc/server/data/logs/server.log"),
        },
        process_patterns={
            # HYDRA-UMC-SERVER's own real camera process supervisor
            # (server.ts) spawns `hydra-umc-vision-streamer stream serve`
            # directly via child_process.spawn - these are real child
            # processes with no systemd unit of their own, so
            # `service.status` can never see them; `process.list` is the
            # one real way to check whether a camera worker is actually
            # alive.
            "vision_streamer_worker": "hydra-umc-vision-streamer",
        },
    )
