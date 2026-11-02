# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/escalation/snapshot.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The node health snapshot: one baseline EvidenceBundle of the read-only health tools, and what changed since the last one.

`take_snapshot` runs, through the normal dispatcher (so the allow-lists, the audit journal and the redaction apply as always), the
health tool for every name the configuration lists: `service.status` for each unit, `network.port_status` for each port,
`network.connectivity` for each target, `storage.usage` for each storage path, `process.list` for each pattern, and
`system.temperature` once. It assembles a bundle with a fixed, honest impact text and saves it as `baseline-<time>.json` (written
whole or not at all). The drift is the list of findings that changed against the previous baseline: the status of a call and each
text or yes/no value of its output; numbers that move by themselves (a temperature, a usage) are not drift. Baselines beyond the
configured `keep` are moved to `archive/`, never deleted.

Run it from a timer (an example unit is in the docs); it is closed unless `snapshot.enabled` is true in the configuration file.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..knowledge.trust import build_tool_request_from_model_output
from ..orchestrator.allowlist import OrchestratorConfig
from ..orchestrator.dispatch import ToolDispatchError, dispatch_tool_request
from ..settings import SnapshotSettings
from .evidence import ObservedResult, assemble_evidence_bundle

IMPACT = "baseline snapshot of the node health: no incident is reported by this bundle"
PREFIX = "baseline-"


class SnapshotError(ValueError):
    """The snapshot is closed or could not be taken."""


def planned_calls(config: OrchestratorConfig) -> list[tuple[str, dict[str, Any]]]:
    """The tool calls a snapshot makes, in a fixed order, from the names the configuration allows."""
    calls: list[tuple[str, dict[str, Any]]] = []
    calls += [("service.status", {"name": name}) for name in config.systemd_units]
    calls += [("network.port_status", {"name": name}) for name in sorted(config.ports)]
    calls += [("network.connectivity", {"name": name}) for name in sorted(config.connectivity_targets)]
    calls += [("storage.usage", {"name": name}) for name in sorted(config.storage_paths)]
    calls += [("process.list", {"name": name}) for name in sorted(config.process_patterns)]
    calls.append(("system.temperature", {}))
    return calls


def _findings(result: dict[str, Any]) -> dict[str, str]:
    """The stable part of a result: its status and every text or yes/no leaf of its output (numbers are left out on purpose)."""
    found = {"status": str(result.get("status"))}

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                walk(f"{prefix}.{key}" if prefix else key, value[key])
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(f"{prefix}.{index}", item)
        elif isinstance(value, bool) or isinstance(value, str):
            found[prefix] = str(value)

    walk("output", result.get("output", {}))
    return found


def drift(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """What changed between two snapshot records (`results` maps a call label to its ToolResult); sorted, so it is repeatable."""
    lines = []
    before, after = previous.get("results", {}), current.get("results", {})
    for label in sorted(set(before) | set(after)):
        if label not in before:
            lines.append(f"{label}: new in this snapshot")
        elif label not in after:
            lines.append(f"{label}: no longer in this snapshot")
        else:
            old, new = _findings(before[label]), _findings(after[label])
            for key in sorted(set(old) | set(new)):
                if old.get(key) != new.get(key):
                    lines.append(f"{label}: {key} was {old.get(key, '(absent)')} and is {new.get(key, '(absent)')}")
    return lines


def _previous(directory: Path) -> dict[str, Any] | None:
    files = sorted(directory.glob(f"{PREFIX}*.json"))
    if not files:
        return None
    try:
        data = json.loads(files[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def take_snapshot(config: OrchestratorConfig, settings: SnapshotSettings, *, now: float | None = None) -> tuple[Path, list[str]]:
    """Takes and saves a baseline; returns its path and the drift against the previous one."""
    if not settings.enabled:
        raise SnapshotError("the snapshot is closed: set snapshot.enabled to true in the configuration file")
    directory = Path(settings.directory)
    directory.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, Any]] = {}
    observed: list[ObservedResult] = []
    for tool, arguments in planned_calls(config):
        label = tool + (f"[{arguments['name']}]" if "name" in arguments else "")
        request = build_tool_request_from_model_output(
            request_id=str(uuid.uuid4()), tool=tool, arguments=arguments, actor="snapshot", reason="periodic baseline snapshot")
        try:
            result = dispatch_tool_request(request, config)
        except ToolDispatchError as error:
            raise SnapshotError(f"{label} was refused: {error}") from error
        results[label] = result
        observed.append(ObservedResult(tool, result))
    bundle = assemble_evidence_bundle(observed, impact=IMPACT, local_validation_result="the snapshot ran the read-only health tools once")
    stamp = datetime.fromtimestamp(time.time() if now is None else now, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    record = {"takenAt": stamp, "bundle": bundle, "results": results}
    previous = _previous(directory)
    target = directory / f"{PREFIX}{stamp}.json"
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    _archive_old(directory, settings.keep)
    return target, ([] if previous is None else drift(previous, record))


def _archive_old(directory: Path, keep: int) -> None:
    files = sorted(directory.glob(f"{PREFIX}*.json"))
    archive = directory / "archive"
    for path in files[:-keep] if len(files) > keep else []:
        archive.mkdir(exist_ok=True)
        os.replace(path, archive / path.name)
