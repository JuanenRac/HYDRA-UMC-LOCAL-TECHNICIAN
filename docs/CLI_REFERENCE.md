<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - docs/CLI_REFERENCE.md
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# CLI Reference

Four real command families: contract validation (Fase 0), real
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

## Exit codes

`0` the work was done. `1` the work ran and its result is an error: a tool that answered with a status that is not `ok`, a contract that
is invalid, an audit chain that is broken. `2` the request was refused before anything ran: a bad argument, a configuration that is wrong,
a policy or allow-list that said no, evidence that is not grounded, a file that cannot be written. (`serve` keeps `1` for a refusal to start.)

## `tools call`

```bash
hydra-umc-local-technician tools call <tool> [--arg NAME=VALUE ...] [--actor <who>] [--reason <why>] [--config <path.json>] [--output <file>]
```

Builds a real `ToolRequest` (via
`knowledge/trust.py`'s own `build_tool_request_from_model_output()` -
refusing an unregistered or unimplemented `<tool>` before anything else
happens) and runs it for real through `dispatch_tool_request()`,
printing the resulting `ToolResult` as JSON to stdout, or writing it to
`--output FILE` (replaced whole, never half written; stdout then carries one
line, `OK: <tool> -> <file>`) so that it can be handed to `escalation` as it is.
Exits `0` when `status` is `"ok"`, `1` when the tool answered with an error and
`2` for a real refusal (printed as `REFUSED: <reason>` to stderr). `--arg` is repeatable
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
allow-list boundary every test already exercises. A config file that is
missing, is not JSON or has the wrong shape is refused in one line
(`REFUSED: invalid --config <path>: <reason>` to stderr, exit `2`).

Two tools are closed until the file turns them on, with a `tools` section
whose switches are real booleans (off when absent; a key it does not know is an
error):

```json
{
  "tools": {
    "journalRead": {"enabled": true, "units": ["hydra-umc-server"]},
    "serverMetrics": {"enabled": true, "targets": {"server": "http://127.0.0.1:3000/metrics"}}
  }
}
```

`journal.read --arg name=hydra-umc-server [--arg lines=100]` returns the last
lines (at most 500) of that unit's journal, redacted. `server.metrics --arg
name=server [--arg prefix=hydra_]` returns the numeric samples (at most 200) of
that endpoint, which is asked with `X-Hydra-Client: technician`. While a switch
is off, or for a name that is not listed, the call is refused before anything is
read.

### Example

```bash
hydra-umc-local-technician tools call service.status --arg name=hydra-umc-server
# -> a real ToolResult JSON, e.g. {"requestId": "...", "status": "ok", "output": {"unit": "hydra-umc-server", "active": true, ...}, ...}
```

## `escalation evidence`

```bash
hydra-umc-local-technician escalation evidence --result <tool.name>=<path.json> [--result ...] --impact "<text>" [--local-validation "<text>"] [--action-attempted "<text>" ...] [--failed-test "<name>" ...] [--output <file>]
```

Assembles a real `EvidenceBundle` (`escalation/evidence.py`'s own
`assemble_evidence_bundle()`) from one or more already-produced
`ToolResult` JSON files - each `--result` names the real tool that
produced it (`tools call ... > result.json` first, then point `--result`
at that file). Every result is re-validated as a real `ToolResult`
before it can become evidence. `--impact` is required and never invented
by this command - state the real, honest impact yourself. Prints the
real bundle as JSON (or writes it to `--output FILE`) and exits `0`, or
`REFUSED: <reason>` to stderr and exits `2` (an empty `--result` set, an empty
`--impact`, or a file that isn't a real valid `ToolResult`).

## `escalation propose`

```bash
hydra-umc-local-technician escalation propose --diagnosis "<text>" --cited-evidence "<evidence text>" [--cited-evidence ...] [--result <tool.name>=<path.json> ...] [--from-bundle <bundle.json>] --scope "<text>" --risk <riskLevel> --step "<text>" [--step ...] --rollback "<text>" [--pre-check "<text>" ...] [--expected-change "<text>" ...] [--explicit-limit "<text>" ...] [--output <file>]
```

Builds a real `MaintenanceProposal` (`escalation/proposal.py`'s own
`propose_maintenance()`) - never generates `--diagnosis`/`--step`/
`--rollback` itself, since there is no inference engine yet; a human
operator supplies them. The one real guardrail this command enforces:
every `--cited-evidence` string must exactly match the `evidence` field
of one of the `--result` files (or one of the reproduction steps of the
`--from-bundle` bundle), or the proposal is refused outright
(`UngroundedEvidenceError`) - "never an unsupported claim"
(`docs/CONTRACTS.md`), enforced mechanically, not just documented.
`--from-bundle` takes an EvidenceBundle that `escalation evidence` assembled, so the
result files do not have to be carried along: its checksum is verified first (a
bundle edited after it was assembled is refused) and what it can ground is its
`reproductionSteps`, the redacted `evidence` text of the tool calls it was made from.
Give `--result`, `--from-bundle` or both. `confirmationRequired` on the printed proposal is never something this
command lets you set - it is always exactly what
`policy/risk_levels.py`'s own policy already says for `--risk`. Nothing
in this codebase can act on a printed proposal yet; this command only
ever builds and validates one.

## `serve --data-dir DIR [--config FILE] [--host 127.0.0.1] [--port 8780] [--token-file FILE]`

Fase 5's read-only local API and web page, described in
[WEB_API.md](WEB_API.md). `--data-dir` holds `tool-results/`, `evidence/` and
`proposals/` folders of the JSON the other commands printed; `--config` is the
same `OrchestratorConfig` file `tools call` takes (the project manifests and
the document index come from it). It answers GET only and binds to loopback;
any other `--host` is refused unless a bearer token of at least 24 characters
is given in `--token-file` or `HYDRA_UMC_LOCAL_TECHNICIAN_TOKEN` (there is no
option to pass it on the command line). Exits `1` with a one-line `REFUSED` on
a bad bind, token, port or config; runs until interrupted, then exits `0`.

## Roadmap: commands later phases will add

Not implemented in this delivery:

- A `contracts schema` command printing the real JSON Schema file for a
  given contract name, once the schema files are also published as a
  standalone artifact.
- A real API integrated into HYDRA-UMC-SERVER/Studio, and voice - the
  rest of Fase 5's own scope beyond the `tools`/`escalation`/`serve`
  commands above.
