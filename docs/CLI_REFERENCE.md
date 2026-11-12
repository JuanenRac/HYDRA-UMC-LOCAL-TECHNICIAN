<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - docs/CLI_REFERENCE.md
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# CLI Reference

Four real command families: contract validation (Fase 0), real
OBSERVE-level tool calls (`tools`, Fase 5's own first slice), and real
`EvidenceBundle`/`MaintenanceProposal` construction (`escalation`, Fase
4/5). There is no model built in (the optional `assistant ask` talks to a chat endpoint you configure) and no HYDRA-UMC-SERVER
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

## Optional features (all closed until the configuration file opens them)

Five more sections of the `--config` file, each with an `enabled` switch that must be a real `true` (default `false`); a key it does not know is an error. Every tuned value (URL, timeouts, limits, validity, directories) lives in the file, never in the code.

```json
{
  "transport": {"enabled": false, "url": "https://dev-server.example/incident", "fromNode": "technician-1", "toNode": "dev-server",
                "secretEnv": "HYDRA_UMC_LOCAL_TECHNICIAN_TRANSPORT_SECRET", "secretFile": "", "timeoutSeconds": 10,
                "allowPlainHttp": false, "maxPayloadBytes": 1000000,
                "nodeTokenFile": "/etc/hydra-umc/technician.node-token", "requireNodeToken": true},
  "runbooks": {"enabled": false, "directory": "/etc/hydra-umc/runbooks", "language": "en"},
  "approvals": {"enabled": false, "trustStore": "/etc/hydra-umc/trust.json", "maxValiditySeconds": 900, "usedNonces": "/var/lib/hydra-umc/nonces.json"},
  "snapshot": {"enabled": false, "directory": "/var/lib/hydra-umc/baselines", "keep": 48},
  "knowledge": {"enabled": false, "directory": "/var/lib/hydra-umc/knowledge-index", "maxStoredFiles": 4096}
}
```

### Stored knowledge index

With `knowledge.enabled` the chunks of every indexed file are also kept on disk (one versioned JSON file per knowledge source, written atomically), so a one-shot `tools call knowledge.search` does not read and split every document again: only the files whose modification time or size changed are read. A store that is damaged, of another format or made for another directory is ignored and written again; a file that vanished leaves the store. `maxStoredFiles` bounds how many files are kept. Closed by default (the index then lives in the process only).

### Outbox transport

- `escalation queue --bundle FILE --outbox DIR [--id ID]` puts a checksum-verified EvidenceBundle into the outbox (same id and same content is a duplicate, never queued twice).
- `escalation send --outbox DIR --config FILE` posts every pending item as a signed `incident-transport/1` message (message id, node names, nonce, time, HMAC-SHA256 over the canonical JSON) and marks it sent only when the receiver answers 2xx with `{"ok": true}`. Anything else leaves it queued. The message carries the token of this node (`Authorization: Bearer ...`, read from `transport.nodeTokenFile`, issued on the development server with `node-token issue`): with `transport.requireNodeToken` on (the default) a send without a readable token is refused before anything leaves, and a revoked token is a `401` that leaves the item queued. The shared secret (at least 24 characters) comes from `secretFile` or the environment variable, never from the command line, and is never printed. Plain `http://` is refused unless the host is loopback or `allowPlainHttp` is set; redirects are not followed. Exit `0` when the queue is empty afterwards, `1` when something is still queued, `2` when refused.

### Runbooks

- `runbook check DIR` validates every `.md` runbook. `runbook run --config FILE --result TOOL=FILE ... [--output FILE]` matches them against tool results and prints the grounded MaintenanceProposals. A runbook is a Markdown file with a front matter (`id`, `risk`, `scope`, `title`, one or more `when: <tool> <path> <operator> <value>`, operators `== != > >= < <= contains exists missing`) and the sections `Diagnosis`, `Steps`, `Rollback` and optionally `Pre-checks`, `Expected changes`, `Limits`; a suffix (`title.es`, `## Diagnosis.pt`) gives the text for one of the eight languages, the unsuffixed text is the fallback. The same results always give the same proposals. The engine only proposes: it has no way to run a step. A shipped example is in `configs/runbooks/`.

### Signed approvals

- `approval keygen --alias A --private FILE --public FILE` makes an Ed25519 key pair on the approver's machine; the private key is refused inside a git working tree, never overwritten, owner-only. It needs the optional `cryptography` package (`pip install .[approvals]`).
- `approval trust add|remove|export|list --config FILE` manages the trust store of public keys by alias (files are exchanged by the public key file; the fingerprint is printed to compare by eye). An alias is never silently pointed at another key.
- `approval sign --private FILE --approver A --action ACTION --proposal FILE --valid-for SECONDS --output FILE` signs one action on one exact proposal (its SHA-256 is inside the signature).
- `approval verify --config FILE --approval FILE --proposal FILE --action ACTION` checks the signature, the alias, the action, the proposal, the validity (never longer than `maxValiditySeconds`) and, when `usedNonces` is set, that the approval was not used before; success yields the record that `policy.execution_mode.decide()` needs in ASSISTED mode. Nothing here executes a step.

### Baseline snapshot

- `tools snapshot --config FILE [--audit-log FILE]` runs the health tools once for every unit, port, connectivity target, storage path and process pattern the configuration lists (and the temperature), saves `baseline-<time>.json` with an EvidenceBundle and prints `DRIFT:` lines for every finding (status, yes/no or text value) that changed since the previous baseline; numbers that move by themselves are not drift. Baselines beyond `keep` are moved to `archive/`, never deleted. Run it from a systemd timer:

```ini
# hydra-umc-technician-snapshot.service
[Service]
Type=oneshot
ExecStart=/opt/hydra-umc/.venv/bin/hydra-umc-local-technician tools snapshot --config /etc/hydra-umc/technician.json
# hydra-umc-technician-snapshot.timer
[Timer]
OnCalendar=hourly
Persistent=true
[Install]
WantedBy=timers.target
```

### Open assistant

- `assistant ask --config FILE (--bundle FILE | --text FILE) --question TEXT [--output FILE]` sends one question about a stored EvidenceBundle (its checksum is verified first) or a text file to a chat endpoint and prints the answer marked `ADVISORY`. It is closed unless `assistant.enabled` is `true`, and enabling it needs the `url` and the `model` the server offers: no model is built in or recommended by the code. Keys of the `assistant` section: `url`, `model`, `apiKeyEnv` / `apiKeyFile` (the key is never taken from the command line and never printed), `timeoutSeconds`, `allowPlainHttp`, `allowRemote`, `maxPromptChars`, `maxResponseChars`, `temperature`, `language` (one of the eight) and `systemPromptFile`.
- Only a loopback address is asked unless `allowRemote` is `true`; plain http to another machine also needs `allowPlainHttp`; an address with credentials is refused and a redirect is never followed. The material and the question are redacted before they are sent and the answer is redacted again, stripped of control characters and cut to `maxResponseChars`.
- The answer is advice for a person: it is never parsed into a `MaintenanceProposal`, a step or an approval. A proposal still needs `propose_maintenance()` with evidence grounded in real tool results, and anything above OBSERVE still needs a signed approval. Exit code 2 (`REFUSED`) when it is closed, misconfigured or the endpoint does not answer a chat completion. Not run against a real language model.

## Roadmap: commands later phases will add

Not implemented in this delivery:

- A `contracts schema` command printing the real JSON Schema file for a
  given contract name, once the schema files are also published as a
  standalone artifact.
- A real API integrated into HYDRA-UMC-SERVER/Studio, and voice - the
  rest of Fase 5's own scope beyond the `tools`/`escalation`/`serve`
  commands above.
