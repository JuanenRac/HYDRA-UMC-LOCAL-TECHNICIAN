<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - docs/CLI_REFERENCE.md
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
============================================================================= -->

# CLI Reference

Three real command families: contract validation (Fase 0), real
OBSERVE-level tool calls (`tools`, Fase 5's own first slice), and real
`EvidenceBundle`/`MaintenanceProposal` construction (`escalation`, Fase
4/5). There is still no inference engine and no HYDRA-UMC-SERVER
integration - `tools call` only ever reaches the same real, already
policy-enforced `dispatch_tool_request()` every unit test already
exercises, never a new authority of its own. A future phase adding the
HYDRA-UMC-SERVER-integrated API or voice extends this same `argparse`
tree (`src/hydra_umc_local_technician/cli.py`) rather than replacing it,
matching the ecosystem's own established CLI conventions (HYDRA-UMC-SDK,
HYDRA-UMC-OPS-AGENT, HYDRA-UMC-DEV-SERVER).

## Installation

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -e .
```

## `--version`

```bash
hydra-umc-local-technician --version
```

Prints the installed package version and exits - reads `__version__`
from `src/hydra_umc_local_technician/__init__.py`, never re-derived or
hardcoded a second time.

## `contracts validate`

```bash
hydra-umc-local-technician contracts validate <payload_file> --contract <ContractName>
```

Validates one JSON document against one of the five real minimal
contracts this project's own plan defines (see `docs/CONTRACTS.md`).
Prints `VALID: <path> (<ContractName>)` and exits `0` on success, or
`INVALID: <path> (<ContractName>): <reason>` to stderr and exits `1` on
any violation - a specific, real reason every time, never a bare
stack trace.

`--contract` accepts exactly one of the five real contract names:
`ToolRequest`, `ToolResult`, `MaintenanceProposal`, `EvidenceBundle`,
`PatchVerificationReport`.

### Examples

```bash
# A real, valid ToolRequest fixture:
hydra-umc-local-technician contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
# -> VALID: tests/fixtures/tool_request.valid.json (ToolRequest)

# A deliberately broken fixture (missing a required field, or an
# unexpected extra one - contracts.py rejects both):
hydra-umc-local-technician contracts validate tests/fixtures/tool_request.invalid.json --contract ToolRequest
# -> INVALID: tests/fixtures/tool_request.invalid.json (ToolRequest): ...
```

### What this command deliberately does not do

It never executes a tool, never talks to a real service, and never
mutates the payload file. It is a pure, offline, stdlib-only check
against `contracts.py`'s own `validate()` - the same function
`knowledge/trust.py`'s `build_tool_request_from_model_output()` calls
internally before ever returning a real `ToolRequest` object. Running
this command by hand against a candidate payload is a way to check a
document against the same rule the real code enforces, not a separate,
looser check.

## `tools list`

```bash
hydra-umc-local-technician tools list
```

Prints every real, registered tool from `policy/tool_matrix.py`, one
per line, tab-separated: `<name> <riskLevel> <implemented|not
implemented> <description>`. All ten real entries are OBSERVE-level and
`implemented` today - there is nothing at a higher risk level to list
yet (see `docs/SECURITY_MODEL.md`).

## `tools call`

```bash
hydra-umc-local-technician tools call <tool> [--arg NAME=VALUE ...] [--actor <who>] [--reason <why>] [--config <path.json>]
```

Builds a real `ToolRequest` (via
`knowledge/trust.py`'s own `build_tool_request_from_model_output()` -
refusing an unregistered or unimplemented `<tool>` before anything else
happens) and runs it for real through `dispatch_tool_request()`,
printing the resulting `ToolResult` as JSON to stdout. Exits `0` when
`status` is `"ok"`, `1` otherwise (including a real refusal, printed as
`REFUSED: <reason>` to stderr). `--arg` is repeatable
(`--arg name=server_http`); each value is parsed as JSON first (so
`--arg topK=5` becomes a real int) and falls back to a plain string.

`--config` points to a JSON file describing a real `OrchestratorConfig`
(`storagePaths`, `ports`, `connectivityTargets`, `systemdUnits`,
`ecosystemRoot`, `logSources`, `processPatterns`, `knowledgeSources` -
the same fields as `orchestrator/allowlist.py`'s own dataclass, camelCase
on the wire). Omitted, this defaults to `default_config()` - the real,
documented CM5 defaults. There is no way to name a raw path/host/port on
the command line itself: every symbolic name `tools call` can ever
resolve still has to already be in this config, the exact same
allow-list boundary every test already exercises.

### Example

```bash
hydra-umc-local-technician tools call service.status --arg name=hydra-umc-server
# -> a real ToolResult JSON, e.g. {"requestId": "...", "status": "ok", "output": {"unitName": "hydra-umc-server", "active": true, ...}, ...}
```

## `escalation evidence`

```bash
hydra-umc-local-technician escalation evidence --result <tool.name>=<path.json> [--result ...] --impact "<text>" [--local-validation "<text>"] [--action-attempted "<text>" ...] [--failed-test "<name>" ...]
```

Assembles a real `EvidenceBundle` (`escalation/evidence.py`'s own
`assemble_evidence_bundle()`) from one or more already-produced
`ToolResult` JSON files - each `--result` names the real tool that
produced it (`tools call ... > result.json` first, then point `--result`
at that file). Every result is re-validated as a real `ToolResult`
before it can become evidence. `--impact` is required and never invented
by this command - state the real, honest impact yourself. Prints the
real bundle as JSON and exits `0`, or `REFUSED: <reason>` to stderr and
exits `1` (an empty `--result` set, an empty `--impact`, or a file that
isn't a real valid `ToolResult`).

## `escalation propose`

```bash
hydra-umc-local-technician escalation propose --diagnosis "<text>" --cited-evidence "<evidence text>" [--cited-evidence ...] --result <tool.name>=<path.json> [--result ...] --scope "<text>" --risk <riskLevel> --step "<text>" [--step ...] --rollback "<text>" [--pre-check "<text>" ...] [--expected-change "<text>" ...] [--explicit-limit "<text>" ...]
```

Builds a real `MaintenanceProposal` (`escalation/proposal.py`'s own
`propose_maintenance()`) - never generates `--diagnosis`/`--step`/
`--rollback` itself, since there is no inference engine yet; a human
operator supplies them. The one real guardrail this command enforces:
every `--cited-evidence` string must exactly match the `evidence` field
of one of the `--result` files, or the proposal is refused outright
(`UngroundedEvidenceError`) - "never an unsupported claim"
(`docs/CONTRACTS.md`), enforced mechanically, not just documented.
`confirmationRequired` on the printed proposal is never something this
command lets you set - it is always exactly what
`policy/risk_levels.py`'s own policy already says for `--risk`. Nothing
in this codebase can act on a printed proposal yet; this command only
ever builds and validates one.

## Roadmap: commands later phases will add

Not implemented in this delivery:

- A `contracts schema` command printing the real JSON Schema file for a
  given contract name, once the schema files are also published as a
  standalone artifact.
- A real API integrated into HYDRA-UMC-SERVER/Studio, and voice - the
  rest of Fase 5's own scope beyond the `tools`/`escalation` commands
  above.
