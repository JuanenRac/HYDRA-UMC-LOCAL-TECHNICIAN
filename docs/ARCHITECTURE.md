<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - docs/ARCHITECTURE.md
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
============================================================================= -->

# Architecture (Fase 0)

Faithful translation of this project's own private development plan
(sections 0, 2-4). It describes the target design across all six phases -
this repository, at Fase 0, only implements the risk-level policy, the
tool matrix, the real contracts, secret redaction and the injection-
defense boundary described in the README. Everything else here is a
documented target, not a claim about what runs today.

## Purpose

HYDRA-UMC-LOCAL-TECHNICIAN is a specialized local AI for the HYDRA-UMC
ecosystem. It runs on the CM5, uses the Hailo-10H accelerator once
installed, and exists to observe, explain, diagnose and assist with
maintaining the ecosystem - it does not aim to replace a general-purpose
foundation model, nor to build one from scratch.

It will be "its own" AI because its contracts, tools, policies, working
memory, documentary sources, tests and safety limits are all its own. The
language engine will be an open model compatible with Hailo-10H,
swappable without changing the rest of the architecture.

**Non-negotiable principle:** the AI never gets authority by generating a
response. Policy, permissions, interlocks and human confirmation decide
every action.

## Why not train a model from scratch

Training a model comparable to commercial assistants needs data, GPUs,
power and evaluation far beyond a CM5's reach - and it adds no value
toward the real goal: keeping HYDRA-UMC correctly maintained.

## Five independent pieces (the target design)

1. **Local inference engine** - a small LLM compatible with Hailo-10H.
   Initial candidates: Qwen2.5-1.5B-Instruct, Qwen2.5-Coder-1.5B or
   Qwen3-1.7B-Instruct. The real choice depends on real Hailo
   compatibility, latency, Spanish-language quality, power draw and the
   specific model's own license - never assumed just because a model is
   open.
2. **Retrievable knowledge (local RAG)** - a local index of approved
   documentation, manifests, contracts, manuals, changelogs, diagnostics
   and runbooks. Never "trained blindly" on the whole disk: every source
   is registered, versioned, and can be excluded.
3. **Tool orchestrator** - deterministic code that queries CM5/service
   state through tools with validated input/output schemas. The LLM
   proposes; the orchestrator validates and only executes if policy
   allows it.
4. **Policy and authorization engine** - classifies every action as
   inform, observe, prepare, privileged, or physical; controls
   confirmations, roles, maintenance windows and audit. This is what
   Fase 0 actually delivers (`policy/risk_levels.py`, `policy/tool_matrix.py`).
5. **User interface** - a local API integrated into HYDRA-UMC-SERVER/
   Studio, a CLI, and later voice. Fase 0 ships only a minimal CLI
   (`contracts validate`) for local development, not this real interface.

## Target architecture (conceptual)

```
Operator: Studio / CLI / Voice
              |
HYDRA-UMC-SERVER (auth, API, session, audit)
              |
   +----------+-----------+
   |                      |
Documentation      LOCAL-TECHNICIAN ORCHESTRATOR      CM5 state
manifests,     <-- RAG + planner + policy -->      services/logs
runbooks              |         |
                HailoRT GenAI   Validated-only tools
                LLM/ASR local        |
                          +----------+----------+
                          |          |           |
                    observation  confirmation  escalation package
                    of the       request       to the future
                    system                     Developer Node
```

**Design rule:** the channel toward services and tools never depends on
free text the model produced. Every call is converted to a structured,
schema-validated object first (see `contracts.py` and
`knowledge/trust.py`) - this is exactly what Fase 0 implements and tests.

## Relationship with the current ecosystem

- **HYDRA-UMC-SERVER** - the authenticated entry point. Will host the
  assistant's endpoint, sessions, roles, confirmations, a summarized
  history and audit events. Must never host the model's own keys nor let
  the LLM bypass authorization.
- **HYDRA-UMC-SDK** - will define versioned contracts for ToolRequest,
  ToolResult, EvidenceBundle, MaintenanceProposal, ApprovalRequest,
  PatchRequest and VerificationReport. Every consumer uses the SDK, never
  improvised JSON. Fase 0's own `contracts/*.schema.json` are this
  project's own local minimal version, to be reconciled with the SDK's
  own contracts once they exist there too.
- **HYDRA-UMC-OS** - will provide the systemd service, an unprivileged
  user, data directories, journald, an update policy, health checks and
  recovery units. This AI is an application of HYDRA-UMC-OS, never a
  modification of the base Raspberry Pi OS system.
- **HYDRA-UMC-UPDATER** - keeps owning install/update logic (signatures,
  versions, download, apply, rollback). This technician can detect
  versions and prepare a plan, never replace that logic.
- **HYDRA-UMC-VOICE-UI and HYDRA-UMC-WATCH** - Voice UI will be the ASR/
  TTS channel; the Watch may show alerts and confirm/reject non-critical
  requests. A watch alone never confirms a dangerous physical action.
- **HYDRA-UMC-DASHBOARD-AI and DATALAKE** - the dashboard presents
  metrics, incidents and traceability; Datalake only receives anonymized/
  allowed events, never full conversations or secrets by default.
- **HYDRA-UMC-HIL-BRIDGE, SAFETY-ZONES and industrial bridges** -
  integrated read-only at first. Physical control actions stay blocked
  until real hardware, proven interlocks, explicit permissions and
  physical-safety validation exist.
- **HYDRA-UMC-DEV-SERVER (future project)** - the programming server on
  an RP5/CM5 with NVMe, VS Code and authorized external assistants. This
  local technician sends an evidence package; DEV-SERVER studies, tests
  and prepares a patch. There must never be a direct automatic-patch
  channel without review, signature and a later test - see
  `contracts/evidence_bundle.schema.json`.

## Trust and security model

See `docs/SECURITY_MODEL.md` for the full six risk levels, the data/
secrets rules, and the real, tested defense against instructions embedded
in retrieved/untrusted content - Fase 0's own literal deliverable.
