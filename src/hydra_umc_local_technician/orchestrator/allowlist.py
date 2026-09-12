# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/orchestrator/allowlist.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
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
from dataclasses import dataclass, field
from pathlib import Path


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

    def resolve_project_manifest_path(self, project: str) -> Path:
        """Real path-traversal defense in depth: PROJECT_NAME_PATTERN
        alone already rejects a `/`, `..`, or any character outside
        `[A-Z0-9-]`, but this also confirms the resolved path is a DIRECT
        child of `ecosystem_root` (never a symlink escape or an
        unexpected nested layout) before ever returning it."""
        if self.ecosystem_root is None:
            raise UnknownAllowlistEntry("no ecosystem_root configured - manifest.read is unavailable")
        if not PROJECT_NAME_PATTERN.fullmatch(project):
            raise UnknownAllowlistEntry(f"{project!r} is not a real HYDRA-UMC/URTC project name")
        candidate = (self.ecosystem_root / project / "hydra-umc.project.json").resolve()
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
    )
