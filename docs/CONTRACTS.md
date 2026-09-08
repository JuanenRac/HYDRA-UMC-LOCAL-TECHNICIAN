<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - docs/CONTRACTS.md
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
============================================================================= -->

# Contracts (Fase 0)

Five real minimal contracts, copied field-for-field from this project's
own private development plan (section 7) - not invented or reinterpreted
in either direction. Each one exists as:

- A normative JSON Schema file under `contracts/*.schema.json` (draft
  2020-12, `required` and `additionalProperties: false` on every one, so
  an extra, unexpected field is a real validation failure, not silently
  ignored).
- A matching, stdlib-only Python validator in `src/hydra_umc_local_technician/contracts.py`,
  mirroring HYDRA-UMC-SDK's own
  `clients/python/src/hydra_umc_sdk/validation.py` pattern - an early,
  portable validation path before a generated client exists, not a
  competing source of truth. The JSON Schema files are normative; this
  module's `REQUIRED` field lists and per-field checks are copied from
  them, field-for-field.
- A pair of real fixtures under `tests/fixtures/` (`<contract>.valid.json`
  and `<contract>.invalid.json`), exercised by both
  `tests/unit/test_contracts.py` and the `contracts validate` CLI command
  (see `docs/CLI_REFERENCE.md`).

These are this project's own local minimal version, to be reconciled
with HYDRA-UMC-SDK's own shared contracts once they exist there too
(see `docs/ARCHITECTURE.md`'s Relationship section) - not assumed to be
the final, ecosystem-wide shape.

## ToolRequest

The only object `knowledge/trust.py`'s
`build_tool_request_from_model_output()` is allowed to produce, and the
only real way any future orchestrator may ever invoke a tool.

| Field | Type | Notes |
| --- | --- | --- |
| `schemaVersion` | string | Must be exactly `"1.0"` in this delivery. |
| `requestId` | string | Non-empty, caller-supplied. |
| `tool` | string | Must name a real, registered entry in `policy/tool_matrix.py`'s `TOOL_MATRIX`. |
| `arguments` | object | The tool's own real arguments - never a free-text blob. |
| `riskLevel` | string | One of the six wire names in `RiskLevel` (`inform`, `observe`, `prepare`, `reversible_operation`, `privileged_change`, `physical_action`) - always derived from the tool's own registered risk level, never supplied directly by a caller. |
| `actor` | string | Who/what is asking - a user, a scheduled check, a future orchestrator component. |
| `reason` | string | A real, human-readable justification. |

## ToolResult

The real outcome of one `ToolRequest`, once a future phase implements a
handler for it. Not produced by anything in this delivery yet.

| Field | Type | Notes |
| --- | --- | --- |
| `requestId` | string | Matches the originating `ToolRequest.requestId`. |
| `status` | string | One of `"ok"`, `"error"`, `"denied"`. |
| `output` | object | The tool's own real output - shape is tool-specific. |
| `evidence` | string | Freeform supporting text - already redacted before this object is ever built. |
| `timestamp` | string | Real, non-empty timestamp. |
| `durationMs` | number | Non-negative. |
| `toolVersion` | string | Which version of the tool handler produced this result. |
| `errorCode` | string or null | Present only when `status` is `"error"` or `"denied"`. |

## MaintenanceProposal

A PREPARE-level proposal - always shown to a human before anything past
it happens.

| Field | Type | Notes |
| --- | --- | --- |
| `diagnosis` | string | What the technician believes is wrong. |
| `citedEvidence` | list (min 1) | Real evidence backing the diagnosis - never an unsupported claim. |
| `scope` | string | What this proposal touches. |
| `risk` | string | One of the six `RiskLevel` wire names. |
| `steps` | list (min 1) | The real, ordered steps a human (or, in a much later phase, an authorized operation) would take. |
| `preChecks` | list | Checks to run before applying any step. |
| `expectedChanges` | list | What should differ afterward, so success is verifiable. |
| `rollback` | string | How to undo it. |
| `confirmationRequired` | boolean | Real boolean - a proposal can never silently imply confirmation is optional. |
| `explicitLimits` | list | What this proposal explicitly does NOT cover. |

## EvidenceBundle

The real escalation package this technician sends toward a future
Developer Node - never a full conversation, never raw, un-redacted logs.

| Field | Type | Notes |
| --- | --- | --- |
| `componentVersions` | object | Real versions of the components involved. |
| `relevantManifests` | list | Real `hydra-umc.project.json` excerpts or references. |
| `redactedLogExcerpts` | list | Always passed through `knowledge/redaction.py` first - never raw. |
| `reproductionSteps` | list (min 1) | Real, concrete steps to reproduce the issue. |
| `failedTests` | list | Which real tests failed, if any. |
| `impact` | string | Real, honest description of the impact. |
| `actionsAttempted` | list | What was already tried. |
| `checksum` | string | Integrity check over the bundle's own content. |
| `date` | string | When the bundle was produced. |
| `localValidationResult` | string | What local validation (if any) already showed. |

## PatchVerificationReport

The real report a future phase produces after testing a proposed patch -
never a claim of success without the checks that back it.

| Field | Type | Notes |
| --- | --- | --- |
| `testedTarget` | object | Must itself contain `package`, `commit`, `version` (all strings). |
| `preCheck` | string | What was verified before applying the patch. |
| `appliedSteps` | list | The real steps actually applied. |
| `healthChecks` | list | Real health checks run afterward. |
| `contractTests` | list | Which real contract tests were run. |
| `result` | string | One of `"passed"`, `"failed"`, `"inconclusive"`. |
| `rollbackExecuted` | boolean | Real boolean - whether a rollback actually happened. |
| `promotionRecommended` | boolean | Real boolean - the report's own recommendation, never assumed. |

## Validating a payload

See `docs/CLI_REFERENCE.md`'s `contracts validate` command, or call
`contracts.validate(contract_name, payload)` directly from Python -
raises `ContractValidationError` with a specific, real reason on any
violation, and returns `None` (never raises) on a valid payload.
