# Changelog: HYDRA-UMC-LOCAL-TECHNICIAN 🤖

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `bump_version.py`.

## Unreleased

(nothing yet)

## [0.0.2] - Fase 3: the first 5 real OBSERVE-level tool handlers

`policy/tool_matrix.py` declared 9 OBSERVE-level tools, all
`implemented=False` since Fase 0. This wires the first 5 to a real
handler (`orchestrator/dispatch.py`): `service.status` (real
`systemctl is-active`, degrading honestly with no guessed reading when
`systemctl` itself isn't on PATH - same pattern as HYDRA-UMC-OPS-AGENT's
own `inventory.py`), `storage.usage` (`shutil.disk_usage`),
`network.port_status` (a real `socket.create_connection` probe),
`system.temperature` (the real Linux thermal-zone sysfs path
HYDRA-UMC-SERVER's own `getSystemMetrics()` reads, same honest
degradation elsewhere), and `manifest.read` (a real
`hydra-umc.project.json` read). The other 4 (`process.list`,
`network.connectivity`, `update.pending`, `logs.read`) stay
`implemented=False` on purpose - each needs its own separate design
(filtering, redaction, or a real HYDRA-UMC-UPDATER integration boundary),
not an oversight.

None of these 5 handlers accepts a raw path/host/port/unit name directly
from `ToolRequest.arguments` - new `orchestrator/allowlist.py` resolves
only a short, symbolic name against a fixed `OrchestratorConfig`
(`default_config()` targets this ecosystem's own real, documented
conventions: `hydra-umc-server.service`, `127.0.0.1:3000`,
`/opt/hydra-umc/server/data`, per HYDRA-UMC-OS's own provisioning
scripts). `manifest.read`'s own project name is checked against the real
`HYDRA-UMC|URTC` naming pattern AND confirmed to resolve as a direct
child of the configured root before ever being read - real defense in
depth against a poisoned document's own text trying to name an arbitrary
target.

Fase 0's own adversarial exit-criterion test file is extended, not
narrowed: a now-implemented tool CAN be turned into a real `ToolRequest`
(the honest, intended new behavior), but new adversarial cases prove a
poisoned "name" argument (a path-traversal shape, an unlisted host/port,
an unlisted systemd unit) is still refused by the allow-list before ever
reaching a real filesystem/network/subprocess call. 85 tests total (was
50), including 28 subtests.

No inference engine, no RAG index, and no HYDRA-UMC-SERVER integration
exist yet - those are still later phases, see README ROADMAP.

## [0.0.1] - Fase 0: inventario y base de seguridad

First phase of six (see the README's own Roadmap section for the full plan).
This one only: the tool/risk-level matrix (`policy/risk_levels.py`, six
levels INFORM through PHYSICAL_ACTION - the top two explicitly
unimplemented; `policy/tool_matrix.py`, a real allowlist of OBSERVE-level
tool names, none wired to a real handler yet), the five real minimal
contracts this project's own plan defines (`contracts/*.schema.json` +
`contracts.py`: ToolRequest, ToolResult, MaintenanceProposal,
EvidenceBundle, PatchVerificationReport), real secret redaction ported
from HYDRA-UMC-OPS-AGENT's own already-tested `log_redaction.py`
(`knowledge/redaction.py`), and this phase's own literal exit criterion:
a real adversarial test (`tests/adversarial/test_injection_defense.py`)
proving a malicious retrieved document can never trigger a tool call or
leak a secret - the orchestrator boundary only ever accepts a real,
schema-validated `ToolRequest` built from already-typed, already-separated
fields (`knowledge/trust.py`'s own `build_tool_request_from_model_output()`),
never free text parsed for a command.

No inference engine, no RAG index, no real tool execution, and no
HYDRA-UMC-SERVER integration exist yet - those are later phases, see
README ROADMAP.
