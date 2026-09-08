# Changelog: HYDRA-UMC-LOCAL-TECHNICIAN 🤖

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `bump_version.py`.

## Unreleased

(nothing yet)

## [0.0.1] - Fase 0: inventario y base de seguridad

First phase of six (this project's own private development plan).
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
