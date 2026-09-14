<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - docs/CLI_REFERENCE.md
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
============================================================================= -->

# CLI Reference (Fase 0)

Fase 0 ships exactly one real command family: contract validation. There
is no inference, no RAG, no real tool execution, and no HYDRA-UMC-SERVER
integration yet - a future phase adding one of those extends this same
`argparse` tree (`src/hydra_umc_local_technician/cli.py`) rather than
replacing it, matching the ecosystem's own established CLI conventions
(HYDRA-UMC-SDK, HYDRA-UMC-OPS-AGENT, HYDRA-UMC-DEV-SERVER).

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

## Roadmap: commands later phases will add

Not implemented in this delivery - listed here only so a reader of this
file knows what is coming and in roughly what order, per the README's
own Roadmap section:

- A `tools list` command (Fase 5) surfacing the real
  `policy/tool_matrix.py` registry and each entry's own
  `implemented` status.
- A `contracts schema` command printing the real JSON Schema file for a
  given contract name, once the schema files are also published as a
  standalone artifact.
- A CLI command that actually invokes `dispatch_tool_request()` for a
  registered OBSERVE-level tool - real handlers already exist for all
  ten `TOOL_MATRIX` entries (`orchestrator/dispatch.py`, Fase 1 and Fase
  3), but no CLI surface calls them yet; that is Fase 5's own scope, the
  same local API/CLI/voice surface as `tools list` above.
