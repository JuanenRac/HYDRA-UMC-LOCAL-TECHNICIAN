# Changelog: HYDRA-UMC-LOCAL-TECHNICIAN 🤖

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `bump_version.py`.

## Unreleased

(nothing yet)

## [0.1.2] - Diagnosis-only mode and an outage-proof escalation queue

- **`policy/execution_mode.py`:** `DIAGNOSIS_ONLY` is the default and refuses every action
  above observe, approval or not. `ASSISTED` still refuses one unless a human approval
  record names that exact action, names a person and carries a signature the caller
  verified against the operator's policy. Model text never enters the decision.
- **`escalation/outbox.py`:** escalations are written to disk first, marked sent only when
  the receiver confirms, survive a restart and a network outage, are never sent twice and
  are never duplicated by queueing the same id again. Eleven new tests.

## [0.1.1] - Fase 5's own first real slice: a real CLI over tool calls and escalation

`cli.py` gains three new real command families, none of them a new
source of authority - each only ever calls the same real,
already-tested code path every unit test already exercises:

- **`tools list` / `tools call`.** `tools call` builds a real
  `ToolRequest` (`knowledge/trust.py`'s own
  `build_tool_request_from_model_output()`) and runs it for real through
  `dispatch_tool_request()`, printing the resulting `ToolResult` as
  JSON. `--config` points to a JSON `OrchestratorConfig`
  (storagePaths/ports/connectivityTargets/systemdUnits/ecosystemRoot/
  logSources/processPatterns/knowledgeSources); omitted, defaults to
  `default_config()`. Still only ever reaches an OBSERVE-level tool -
  nothing above OBSERVE is implemented anywhere in this codebase, so
  this CLI cannot reach it either.
- **`escalation evidence`.** Builds a real `EvidenceBundle`
  (`escalation.evidence.assemble_evidence_bundle()`) from one or more
  already-produced `ToolResult` JSON files (typically
  `tools call ... > result.json` first).
- **`escalation propose`.** Builds a real `MaintenanceProposal`
  (`escalation.proposal.propose_maintenance()`), grounded against the
  same real `ToolResult` files - never generates `diagnosis`/`steps`/
  `rollback` itself, a human operator supplies them.

Deliberately scoped to what lives inside this one repo - the rest of
Fase 5 (a real API integrated into HYDRA-UMC-SERVER/Studio, then voice)
stays separate, cross-repo work for a later delivery, not rushed into
this one. 11 new tests.

## [0.1.0] - Fase 4: escalation - real EvidenceBundle assembly and MaintenanceProposal construction

New `escalation/` package, two independent pieces:

- **`escalation/evidence.py` - `assemble_evidence_bundle()`.** Turns a real
  batch of already-run, already-validated OBSERVE-level `ToolResult`s into
  a real, `contracts.validate("EvidenceBundle", ...)`-passing bundle -
  mirrors HYDRA-UMC-OPS-AGENT's own `incident.py`: pure derivation from
  already-observed data, never an AI call. `componentVersions`,
  `relevantManifests`, `redactedLogExcerpts` and `reproductionSteps` are
  mechanical extraction from real tool output; `checksum` is a real
  SHA-256 over the bundle's own deterministic content. Every input
  `ToolResult` is re-validated here too, never merely trusted because a
  caller labeled it one.
- **`escalation/proposal.py` - `propose_maintenance()`.** A real
  constructor/validator for `MaintenanceProposal`, deliberately NOT a
  generator: there is no inference engine yet (Fase 2), and this
  project's own non-negotiable principle - the AI never gets authority by
  generating a response - rules out fabricating a diagnosis or a
  remediation plan. Today only a human operator supplies
  `diagnosis`/`steps`/`rollback`; the one real guardrail this module adds
  beyond bare contract validity is that every `citedEvidence` entry must
  be grounded - it must literally be the `evidence` field of some
  already-observed `ToolResult` passed as `evidence_pool`, or the
  proposal is refused outright (`UngroundedEvidenceError`). `confirmationRequired`
  is never a caller-supplied boolean - it is always exactly what
  `policy/risk_levels.py`'s own `POLICIES` already says for the proposal's
  declared `risk`.

Nothing in this codebase can act on a `MaintenanceProposal` yet - Fase 4
only ever builds and validates one; execution stays Fase 5+'s own,
separate, human-confirmed concern. 15 new tests.

## [0.0.9] - Fase 1: retrievable knowledge index (real, complete)

`knowledge/index.py` is a real, local TF-IDF search engine over an
allow-listed root directory - the tokenize/build_index/search kernel is
ported unchanged from HYDRA-UMC-DOCS-QA's own already-tested `index.py`
(same accented-Latin + CJK-bigram tokenizer, same fenced-code-block
heading guard); new here is bounded ingestion for both Markdown
(heading-scoped chunks) and JSON (one whole, pretty-printed file per
chunk - a manifest or contract schema is never usefully split
mid-object), capped by a real per-file byte size and a total indexed-file
count so even a legitimately allow-listed root cannot become an
unbounded read. Wired as the tenth OBSERVE-level tool, `knowledge.search`
(`orchestrator/dispatch.py`), through a new
`OrchestratorConfig.resolve_knowledge_source()` (`orchestrator/allowlist.py`)
- a caller only ever names an already allow-listed symbolic source, never
a raw path, and every real match returned is still wrapped as
`UntrustedText` before it ever leaves the handler, same injection-defense
boundary every other tool already respects. 16 new tests.

## [0.0.8] - Real CI bug fixed: update.pending's own optional-dependency tests

`UpdatePendingTests` documents its own intent in its docstring - stay
deterministic and offline "regardless of whether the optional
`update-check` extra happens to be installed" - but
`unittest.mock.patch.multiple()` (used without `create=True`) can only
patch a module attribute that already exists. `dispatch.py`'s own
lazy `hydra_umc_updater` import only ever *defined* `_updater_parse_manifest`
and friends on a successful import; on `ImportError` it left them
undefined entirely. Every environment without `hydra-umc-updater`
installed as a sibling package - including this repo's own GitHub
Actions CI - hit a real `AttributeError` on 5 of these tests, not the
honest degraded-mode result the suite was written to exercise. Fixed
by defining those names as `None` placeholders on `ImportError`; every
real call site already guards on `_HAS_UPDATE_CHECK` first, so this
changes no runtime behavior.

## [0.0.7] - Python validation now matches the normative schemas' own type/format constraints

- **List elements were never type-checked:** `_require_list()` only
  checked the container's own type/length - every list field (across
  all 5 contracts) declares `"items": {"type": "string"}` in its
  normative `contracts/*.schema.json`, but a number, `null`, or nested
  object anywhere in the list used to sail through silently. Now
  rejected element-by-element, matching the schema.
- **`durationMs` accepted non-finite values:** `duration < 0` alone is
  not a finiteness check - NaN compares `False` against everything, and
  Python's own `json.loads()` accepts the bare `NaN`/`Infinity` tokens
  by default even though real JSON has no such literals. Now rejected
  via an explicit `math.isfinite()` check.
- **`timestamp`/`date` ignored their own declared `"format": "date-time"`:**
  a JSON Schema validator does not enforce `format` unless a
  format-checking plugin/flag is explicitly turned on, and this
  hand-written validator never checked it at all - any non-empty string
  passed. New `_require_iso_timestamp()` parses with
  `datetime.fromisoformat()` (Python 3.11+, already required), applied
  to `ToolResult.timestamp` and `EvidenceBundle.date`.
- 5 new regression tests.

## [0.0.6] - Fase 3 complete: the 9th and last real OBSERVE-level tool handler (update.pending)

`update.pending`'s own real integration boundary is now wired - the one
tool that genuinely needed a dependency on another project rather than
just its own filtering/allow-list design. Reuses HYDRA-UMC-UPDATER's
already-tested GitHub discovery (`github_client.fetch_all`), manifest
parsing (`project_manifest.parse_manifest`) and version comparison
(`version_parse.Version`) instead of a second, silently-drifting copy of
any of it - the same "delegate to the real logic elsewhere" principle
HYDRA-UMC-OS-REBUILDER's own `ecosystem_plan.py` already applies.
`hydra-umc-updater` is an OPTIONAL dependency (the new `update-check`
extra) - imported lazily, guarded by `_HAS_UPDATE_CHECK`, so every other
tool in this package stays usable on a bare stdlib-only install;
`update.pending` itself degrades honestly (`available: false`) when the
extra is not installed, never a crash on import. The project name
argument reuses `manifest.read`'s own real allow-list boundary
(`resolve_project_manifest_path` - `PROJECT_NAME_PATTERN` + must resolve
under `ecosystem_root`) rather than a second, redundant one.

**Fase 3 is now complete: all 9 of the 9 declared OBSERVE-level tools
have a real handler** (`service.status`, `storage.usage`,
`network.port_status`, `network.connectivity`, `system.temperature`,
`manifest.read`, `logs.read`, `process.list`, `update.pending`). Also
fixed two real, unrelated staleness bugs found while closing this out:
`docs/SECURITY_MODEL.md` still said "every single one is still
`implemented=False`" (a Fase 0 sentence never updated across 6/9, 7/9 and
8/9), and this package's own `pyproject.toml` description still said
"Fase 0 only".

Verified: 117 tests + 28 subtests passing (2 skipped on a host with no
real `/proc`, exercised for real on Linux CI) (`tests/unit/`,
`tests/adversarial/`), `tools/ci_validate.py` PASS.

## [0.0.5] - Fase 3: an 8th real OBSERVE-level tool handler (process.list)

`process.list`'s own separate design need ("which processes even count
as relevant is a real open design question") is now answered the same
way every other handler here already answers it: only ever a symbolic
name an operator explicitly allow-listed. New `OrchestratorConfig.process_patterns`
(symbolic name -> a real substring) resolves to a real read-only
`/proc/<pid>/cmdline` scan (`dispatch._list_proc_matches()`) - the same
mechanism `ps` itself is built on, no subprocess spawned - capped at 20
real matches, never a raw, unfiltered process table. Honestly degrades
with `available: false` on a host with no real `/proc` (this dev machine
included), the same convention `system.temperature`/`service.status`
already use. `default_config()`'s new real entry: `vision_streamer_worker`
-> `hydra-umc-vision-streamer`, HYDRA-UMC-SERVER's own real camera
process supervisor spawns these directly via `child_process.spawn` with
no systemd unit of their own, so `service.status` can never see them -
`process.list` is the one real way to check whether a camera worker is
actually alive.

Fase 3 is now 8 of 9 tools (`update.pending` remains - see
`dispatch.py`'s own module doc comment for why it needs its own
separate design).

Verified: 109 tests + 28 subtests passing (2 more skipped on a host with
no real `/proc`, exercised for real on Linux CI) (`tests/unit/`,
`tests/adversarial/`), `tools/ci_validate.py` PASS.

## [0.0.4] - Fase 3: a 7th real OBSERVE-level tool handler (logs.read)

`logs.read`'s own separate design need (called out since Fase 3's first
slice) is now real: `OrchestratorConfig.log_sources` (a new, separate
symbolic-name namespace, same pattern as `connectivity_targets`) resolves
to exactly one real, allow-listed FILE - never a directory or glob, never
a raw path a retrieved document could supply. `dispatch._handle_logs_read()`
tails at most 500 lines (default 50) within a bounded 1 MiB read window
of the file's own tail (so a request against a log that has grown large
still costs a fixed amount of memory, not one scaling with the file's own
size), and pipes every line through `knowledge.redaction.redact_lines()`
before it ever leaves the handler. A missing log file is a real, honest
`exists: false` result, not an error - a service that has not logged
anything yet is a legitimate state, not a failure. `default_config()`'s
own real entry: `server_log` -> HYDRA-UMC-SERVER's own documented
`LOG_FILE` constant, at its real installed path on the CM5.

Fase 3 is now 7 of 9 tools (`process.list` and `update.pending` remain -
see `dispatch.py`'s own module doc comment for why each needs its own
separate design).

Verified: 103 tests + 28 subtests passing (`tests/unit/`,
`tests/adversarial/`), `tools/ci_validate.py` PASS.

## [0.0.3] - Fase 3: a 6th real OBSERVE-level tool handler (network.connectivity)

Wires `network.connectivity` to a real handler in
`orchestrator/dispatch.py`, a genuinely different check from
`network.port_status` (already real since 0.0.2): a real HTTP GET
against an allow-listed URL, reporting the endpoint's own real status
code, rather than a bare TCP connect - the same real distinction
HYDRA-UMC-OPS-AGENT's own `inventory.py` already draws between
`check_systemd_unit_health()` and `check_http_health()`. Only
`http`/`https` schemes are ever opened (mirrors that same file's own
`_SUPPORTED_HTTP_SCHEMES` guard); a real HTTP error response (4xx/5xx)
is still reported as `reachable: true` with the real status code, since
the endpoint did answer - a genuinely different, more informative
outcome than a connection that never got a response at all.

New `orchestrator/allowlist.py` field `connectivity_targets` (symbolic
name -> a real, fixed URL), kept in its own namespace rather than
folded into `ports` - conflating "is one of this host's own expected
services listening" with "can this host reach a real endpoint and get
an answer" would make the tool answer the wrong question for whichever
entry happened to be resolved. `default_config()` now also targets
HYDRA-UMC-SERVER's own real `GET /api/hydra-info`.

Fase 3 is now 6 of 9 tools (`process.list`, `update.pending`,
`logs.read` remain for a later slice, each for the same real reasons
already documented in `dispatch.py`'s own module comment). 8 new tests
(3 real local HTTP servers via `http.server.HTTPServer` covering
reachable/HTTP-error/unreachable, an allow-list refusal, a
non-http(s)-scheme refusal, plus 2 direct `resolve_connectivity_target`
unit tests and 1 new adversarial case proving a poisoned document's own
text can never smuggle in an arbitrary URL). 93 tests total (was 85),
including 28 subtests. README x7 + CHANGELOG updated throughout.

Verified: 93 tests + 28 subtests, ci_validate PASS.

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
