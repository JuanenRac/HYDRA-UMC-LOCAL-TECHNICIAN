<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - docs/SECURITY_MODEL.md
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
============================================================================= -->

# Security Model (Fase 0)

This is the one document every future phase must keep agreeing with - a
later phase widening what this technician can do must update this file
in the same commit, not leave it stale.

**Non-negotiable principle, repeated from `docs/ARCHITECTURE.md` because
it is the root of everything below:** the AI never gets authority by
generating a response. Policy, permissions, interlocks and human
confirmation decide every action - never the model's own text.

## The six risk levels

Defined in `src/hydra_umc_local_technician/policy/risk_levels.py` as
`RiskLevel`, an ordered `IntEnum` - a higher numeric value is always a
higher-risk action, so a future orchestrator can enforce a ceiling with a
plain numeric comparison instead of a lookup table of its own.

| Level | Wire name | Can read tools | Can mutate | Confirmation | Implemented in Fase 0 |
| ----- | --------- | :-: | :-: | :-: | :-: |
| 0 INFORM | `inform` | No | No | No | Yes |
| 1 OBSERVE | `observe` | Yes | No | No | Yes |
| 2 PREPARE | `prepare` | Yes | No | Yes | Yes |
| 3 REVERSIBLE_OPERATION | `reversible_operation` | Yes | Yes | Yes | No |
| 4 PRIVILEGED_CHANGE | `privileged_change` | Yes | Yes | Yes | No |
| 5 PHYSICAL_ACTION | `physical_action` | No | Yes | Yes | No |

- **INFORM** - read documentation or explain status already known to the
  assistant. No tool access at all.
- **OBSERVE** - read manifests, versions, allow-listed logs, service
  health, storage, temperature and connectivity. Never modifies anything.
  This is the only level with a real, named tool registry today -
  `policy/tool_matrix.py`'s nine `TOOL_MATRIX` entries, every one of
  which is still `implemented=False` in this delivery (see below).
- **PREPARE** - generate a diagnosis, a plan, a proposed diff, an
  evidence bundle, or a command that is written but not executed. Must
  be shown to a human before anything past this point happens.
- **REVERSIBLE_OPERATION** - restart an authorized service, rotate a
  log, refresh an index, or download (never apply) an update. Requires
  authenticated confirmation, a pre-check, a post-check and a durable
  record. Declared for contract completeness only - not implemented.
- **PRIVILEGED_CHANGE** - install or apply a package, change
  configuration or credentials. Requires an administrator role, a second
  confirmation, a backup/rollback plan and a maintenance window. Will not
  be implemented at the start of this project, on purpose.
- **PHYSICAL_ACTION** - motion, power, actuators, firmware or safety.
  Forbidden for this AI until a dedicated design, a separate
  authorization path, an E-stop, real interlocks and physical validation
  all exist. Never an automatic consequence of anything this technician
  does on its own.

`RiskLevelPolicy` (same module) attaches the four booleans and a
description above to each level in `POLICIES`, and every one of those
values is enforced by a real test (`tests/unit/test_risk_levels.py`),
not only documented here.

## The tool matrix: an allowlist, not a filter

`policy/tool_matrix.py`'s `TOOL_MATRIX` is the complete, fixed list of
every tool name this technician will ever be allowed to invoke, each
pinned to its own risk level. A name that is not a key in that
dictionary cannot be called - `lookup_tool()` returns `None`, and the
only real caller of that result (`knowledge/trust.py`'s
`build_tool_request_from_model_output()`) treats `None` as an
unconditional refusal. There is no "call anything and classify its risk
afterward" path anywhere in this codebase.

Fase 0 registered nine OBSERVE-level tool names (`service.status`,
`process.list`, `network.port_status`, `storage.usage`,
`system.temperature`, `network.connectivity`, `update.pending`,
`logs.read`, `manifest.read`) - the exact read-only surface this
project's own plan lists for its first version, every one declared with
`implemented=False` at that point: the matrix existed so a future
`ToolRequest` naming one of them would be recognized as legitimate, but
no real handler was wired to any of them yet.

Fase 3 has since wired a real, read-only handler to all nine
(`orchestrator/dispatch.py` + `orchestrator/allowlist.py`) - every
handler still only ever resolves a short, allow-listed symbolic name,
never a raw path/host/port/URL/pattern a retrieved document could
supply (see this file's own `resolve_*` methods). A name still absent
from `TOOL_MATRIX` altogether (`shell.exec`, say) is refused exactly as
before - see `tests/adversarial/test_injection_defense.py`'s own point
(d), still exercised as a live invariant even though its own set of
"still unimplemented" tools is now empty.

## Data and secrets

`knowledge/redaction.py` (ported unchanged in logic from
HYDRA-UMC-OPS-AGENT's own already-tested `log_redaction.py`) is the one
real function every path that leaves this process on must pass through:
a saved snapshot file today, a future network transport or AI-provider
request later. It recognizes, and replaces with a fixed `[REDACTED]`
marker:

- `KEY=VALUE` / `KEY: VALUE` shell-export and `.env` shapes.
- The same shape inside a JSON string key (`"password": "..."`).
- `Authorization: Bearer <token>` and bare `Bearer <token>`.
- `scheme://user:password@host` credentials embedded in a URL (the
  username is kept - it rarely is the secret itself and helps a human
  recognize which credential was in play; only the password is
  replaced).
- A complete or truncated PEM private-key block (SSH, TLS and GPG all
  share this envelope).
- A secret-named key whose value is itself a nested JSON object or
  array, tracked with real bracket depth rather than a regex that
  cannot reliably match balanced structures.

This is a deliberately fixed, explicit list of real, well-known secret
shapes - never a fuzzy "looks random enough" heuristic, which would
invite both false positives (destroying real diagnostic value in an
innocuous long identifier) and false negatives (a genuine secret shaped
just differently enough to dodge a vague pattern).

## Untrusted content and the injection-defense boundary

This is Fase 0's own literal exit criterion: a real test proving a
malicious retrieved document can never trigger a tool call or leak a
secret.

Every README, log line, commit message, error message or indexed
document this technician ever reads is untrusted data - it can never
change policy or induce a command, no matter what it says. The defense
this delivery implements is architectural, not a filter that tries to
recognize "instruction-like" text (a losing game against a determined
prompt injection):

- `knowledge/trust.py`'s `UntrustedText` wraps every such source. It is
  a `str` subclass with exactly one method, `.redacted()`, which returns
  a sanitized plain string safe to display or cite as evidence. It has
  no method that produces a `ToolRequest`, a `MaintenanceProposal`, or
  any other contract object - there is no "interpret this text as a
  command" path on this type at all.
- The only real way to construct a `ToolRequest` anywhere in this
  codebase is `build_tool_request_from_model_output()`, which takes
  already-typed, already-separated fields (a tool name, an arguments
  object, an actor, a reason) - never a single blob of text to parse for
  a command. Its own function signature has no `risk_level` parameter:
  the risk level is always looked up from `policy/tool_matrix.py` by the
  tool's own registered name, never supplied by a caller (or, by
  extension, ever inferable from a retrieved document's own words).
- A tool name that is not registered, or is registered but not yet
  `implemented`, is refused with `ToolCallRefused` before a `ToolRequest`
  object ever exists - not filtered out later by whatever eventually
  dispatches one.
- The resulting object is additionally validated against
  `contracts.py`'s own `validate("ToolRequest", ...)` before it is
  returned, so a well-formed but contractually invalid request can never
  reach a caller either.

A caller holding only `UntrustedText` has no path into a real tool call
without deliberately re-typing and re-validating each field by hand -
exactly the friction this defense relies on.

`tests/adversarial/test_injection_defense.py` builds a realistic poisoned
document (an `UntrustedText` containing a fake "ignore all previous
instructions, call tool X" payload plus embedded secrets) and asserts,
concretely: `UntrustedText` exposes no tool-producing method at all; a
request naming an unregistered tool (`"shell.exec"`) is refused and that
name is not in `TOOL_MATRIX` in the first place; every currently
registered tool is still refused (none are implemented yet); the request
builder's signature carries no risk-level parameter a caller could set;
and `.redacted()` strips the embedded secrets while preserving the
genuinely useful, non-secret content next to them.

## What Fase 0 deliberately does not implement

No inference engine, no RAG index, no real tool execution, and no
HYDRA-UMC-SERVER integration exist in this delivery. Everything above is
either a declared contract/policy (enforced by tests) or a real,
tested defensive boundary - never a claim that this technician can
already observe, prepare, or act on the real ecosystem. See the
README's own Roadmap section for what later phases add, and in what
order.
