# Contributing to HYDRA-UMC-LOCAL-TECHNICIAN 🤖

We welcome contributions to this ecosystem's own local, policy-gated AI
maintenance technician.

## Technology Stack

- **Language**: Python 3.11+.
- **Dependencies**: stdlib only, deliberately, for Fase 0 - the
  policy/tool-matrix/contract/redaction core needs no dependency at all.
  HailoRT GenAI and any RAG-indexing library are later-phase additions,
  added only once that phase's own code genuinely needs them, never
  speculatively.

## Guidelines

1. **The AI never gets authority by generating a response.** This is the
   one principle every other rule below exists to protect. Do not add a
   code path where a model's own output text is parsed for a command, a
   risk level, or a permission - every real action must go through a
   typed, schema-validated object built from already-separated fields
   (see `knowledge/trust.py`'s own `build_tool_request_from_model_output()`).
2. **A tool must be registered in `policy/tool_matrix.py` before it can
   ever be called - no exceptions.** Do not add a code path that invokes
   a tool name outside `TOOL_MATRIX`, and do not flip an entry's own
   `implemented` flag to `True` without also adding a real handler AND
   real tests proving that handler enforces its own declared risk level
   (`can_read_tools`/`can_mutate`/`requires_confirmation` from
   `policy/risk_levels.py`'s own `POLICIES`).
3. **`PRIVILEGED_CHANGE` and `PHYSICAL_ACTION` stay unimplemented.** Both
   are declared in `RiskLevel` for contract completeness only. Do not
   implement a tool at either level without first updating
   `docs/SECURITY_MODEL.md` to describe the new design, authorization
   path and (for `PHYSICAL_ACTION`) real interlocks - this is a
   deliberate, permanent gate, not an oversight to "complete."
4. **Untrusted content stays untrusted.** A README, log line, commit
   message, error message or indexed document is always wrapped as
   `UntrustedText` (`knowledge/trust.py`) before this codebase touches
   it. Do not add a method to `UntrustedText` that produces a
   `ToolRequest` or any other contract object, and do not add a second
   way to construct a `ToolRequest` that bypasses
   `build_tool_request_from_model_output()`'s own validation.
5. **A contract's normative source is its JSON Schema file.** If you
   change a field in `contracts/*.schema.json`, update
   `src/hydra_umc_local_technician/contracts.py`'s own `REQUIRED` list
   and validator function in the same commit, plus both fixtures under
   `tests/fixtures/` - the schema file, the Python validator and the
   fixtures must never drift from each other.
6. **Secret redaction changes need a real, concrete example.** A new
   pattern added to `knowledge/redaction.py` needs a real fixture in
   `tests/unit/test_redaction.py` showing the exact secret shape it
   catches and a case showing it does not over-match innocuous content -
   same rigor as the existing patterns' own comments (each cites the
   real leak shape it defends against).
7. **This delivery (Fase 0) only ever declares and validates - it does
   not yet act.** Do not add a real inference engine, RAG index, tool
   execution, or HYDRA-UMC-SERVER integration without first checking
   which later phase (see this project's own private development plan's
   phase list, summarized in the README's own Roadmap section) actually
   owns that piece, and updating both the README and
   `docs/ARCHITECTURE.md` to match.
