<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-LOCAL-TECHNICIAN banner" width="100%">
</p>

# 🤖 HYDRA-UMC-LOCAL-TECHNICIAN

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🛡️ Local, Policy-Gated AI Maintenance Technician

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only core">
  <img src="https://img.shields.io/badge/Phase-3%20of%206%20complete-367BF5.svg" alt="Fase 3 of 6 complete">
</p>

> **Status: v0.0.8, functional - Fase 3 of 6 complete (tool
> orchestrator).** Fase 0 defined the real risk-level policy
> (`policy/risk_levels.py`), a fixed tool allowlist
> (`policy/tool_matrix.py`), the five real minimal contracts every future
> tool call must validate against (`contracts/*.schema.json` +
> `contracts.py`), real secret redaction ported from
> HYDRA-UMC-OPS-AGENT's own already-tested `log_redaction.py`, and Fase
> 0's own literal exit criterion: a real adversarial test proving a
> malicious retrieved document can never trigger a tool call or leak a
> secret. Fase 3 wires all 9 of the declared OBSERVE-level tools
> to a real handler (`orchestrator/dispatch.py`): `service.status`,
> `storage.usage`, `network.port_status`, `network.connectivity`,
> `system.temperature`, `manifest.read`, `logs.read`, `process.list` and `update.pending` - each resolving only a short,
> allow-listed symbolic name (`orchestrator/allowlist.py`), never a raw
> path/host/port/URL a retrieved document could supply. No inference
> engine, no RAG index, and no HYDRA-UMC-SERVER integration exist yet -
> see [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for the exact
> command surface that exists today.

---

**Honesty check - what actually runs today:** the risk-level policy (`policy/risk_levels.py`), the fixed tool allowlist (`policy/tool_matrix.py`), the five contract validators (`contracts.py` + `contracts/*.schema.json`), the injection-defense boundary (`knowledge/trust.py`, `knowledge/redaction.py`), and now all 9 declared OBSERVE-level tool handlers (`orchestrator/dispatch.py` + `orchestrator/allowlist.py`: `service.status`, `storage.usage`, `network.port_status`, `network.connectivity`, `system.temperature`, `manifest.read`, `logs.read`, `process.list`, `update.pending`) are real and tested (117 tests plus 28 subtests passing across `tests/unit/` and `tests/adversarial/`) - Fase 3 is complete. `update.pending` needs the optional `hydra-umc-updater` dependency (the `update-check` extra) to actually check GitHub, and degrades honestly (`available: false`) without it. There is still no inference engine, no RAG index, and no HYDRA-UMC-SERVER integration anywhere in this repository - Fases 1, 2, 4 and 5 in the Roadmap below remain entirely aspirational, with zero code behind them. See `CHANGELOG.md` for exactly what has shipped so far.

---

## 1. 🛠️ TECHNICAL OVERVIEW

HYDRA-UMC-LOCAL-TECHNICIAN is a specialized local AI for the HYDRA-UMC
ecosystem itself: it observes, explains, diagnoses and proposes
maintenance for the ecosystem's own services and nodes - it never trains
a new foundation model, and it never acts by generating text. Its target
platform is the CM5, using the Hailo-10H accelerator once installed, but
nothing in this delivery needs it yet: everything through Fase 3 is pure
Python reading real host state and validating pure data - no model
inference anywhere in this codebase yet.

**Non-negotiable principle:** the AI never gets authority by generating
a response. Policy, permissions and human confirmation decide every real
action - never the model's own words.

This delivery ships five real, independently useful pieces:

1. **Risk-level policy** (`policy/risk_levels.py`) - six ordered levels,
   `INFORM` through `PHYSICAL_ACTION`, each with a real, tested policy
   (can it read a tool, can it mutate, does it require confirmation, is
   it implemented). The top two levels are declared for contract
   completeness only - genuinely not implemented anywhere in this
   codebase.
2. **Tool matrix** (`policy/tool_matrix.py`) - a fixed allowlist of nine
   real `OBSERVE`-level tool names. A tool name absent from this
   dictionary can never be called, full stop - all 9 are now wired
   to a real handler (see 5 below).
3. **Real contracts** (`contracts/*.schema.json` + `contracts.py`) -
   `ToolRequest`, `ToolResult`, `MaintenanceProposal`, `EvidenceBundle`
   and `PatchVerificationReport`, each with a normative JSON Schema file
   and a matching stdlib-only Python validator copied from it
   field-for-field.
4. **Injection-defense boundary** (`knowledge/trust.py` +
   `knowledge/redaction.py`) - untrusted content (a README, a log line, a
   commit message) is always wrapped as `UntrustedText`, a type with no
   method that can ever produce a tool call. The only real way to build a
   `ToolRequest` takes already-typed, already-separated fields and
   refuses any unregistered or unimplemented tool name before the object
   ever exists.
5. **Tool orchestrator** (`orchestrator/dispatch.py` +
   `orchestrator/allowlist.py`, Fase 3) - `dispatch_tool_request()` runs
   an already-validated `ToolRequest` for real and returns a real
   `ToolResult`: `service.status` (real `systemctl is-active`),
   `storage.usage` (`shutil.disk_usage`), `network.port_status` (a real
   socket probe), `network.connectivity` (a real HTTP GET reporting the
   endpoint's own real status code - a genuinely different check from
   `network.port_status`, same real distinction HYDRA-UMC-OPS-AGENT's own
   `inventory.py` draws between a bare TCP connect and a real health GET),
   `system.temperature` (the real Linux thermal-zone sysfs path),
   `manifest.read` (a real `hydra-umc.project.json` read), `logs.read`
   (a bounded, redacted tail of one allow-listed log file),
   `process.list` (a real, allow-listed `/proc/<pid>/cmdline` substring
   match), and `update.pending` (reuses HYDRA-UMC-UPDATER's own real
   GitHub discovery and version comparison, optional dependency). None of
   these accepts a raw path/host/port/URL/unit name/pattern directly -
   only a short symbolic name resolved through a fixed
   `OrchestratorConfig`, so a poisoned document's own text can never name
   an arbitrary real target, only ever a name already on the allow-list.

```
$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
VALID: tests/fixtures/tool_request.valid.json (ToolRequest)

$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.invalid.json --contract ToolRequest
INVALID: tests/fixtures/tool_request.invalid.json (ToolRequest): ...
```

There is no default/bare invocation and no GUI in this delivery - see
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for the full, real command
surface.

## 2. 🧱 ARCHITECTURE & DESIGN DECISIONS

- **The AI never gets authority by generating a response.** Every design
  decision in this delivery exists to protect this one principle - see
  [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) for the full model.
- **A tool must be registered before it can ever be called.**
  `policy/tool_matrix.py`'s `TOOL_MATRIX` is the complete, fixed list;
  `lookup_tool()` returning `None` is an unconditional refusal, never a
  case to guess a default risk level for.
- **Untrusted content can never become a command.** The defense is
  architectural (a type with no tool-producing method), not a filter
  that tries to recognize "instruction-like" text - a losing game
  against a determined prompt injection. See
  `tests/adversarial/test_injection_defense.py`, Fase 0's own literal
  exit criterion.
- **A contract's normative source is its JSON Schema file.**
  `contracts.py`'s field lists and validators are copied from
  `contracts/*.schema.json`, field-for-field, mirroring HYDRA-UMC-SDK's
  own `validation.py` convention - not a second, independent source of
  truth.
- **Secret redaction reuses already-tested code.**
  `knowledge/redaction.py` is a byte-for-byte port (only the header
  comment differs) of HYDRA-UMC-OPS-AGENT's own already-tested
  `log_redaction.py` - the underlying problem (recognize real, well-known
  secret shapes without a fuzzy heuristic) is identical here.
- **`PRIVILEGED_CHANGE` and `PHYSICAL_ACTION` stay unimplemented.** A
  deliberate, permanent gate until a dedicated design, a separate
  authorization path and, for physical action, real interlocks exist -
  not an oversight to complete later.
- **This delivery only ever declares and validates - it does not act.**
  No inference engine, no RAG index, no real tool execution, and no
  HYDRA-UMC-SERVER integration exist anywhere in this repository yet.

## 📂 DIRECTORY STRUCTURE

```
HYDRA-UMC-LOCAL-TECHNICIAN/
├── src/hydra_umc_local_technician/
│   ├── policy/
│   │   ├── risk_levels.py    # RiskLevel + RiskLevelPolicy: the six levels, real per-level policy
│   │   └── tool_matrix.py    # TOOL_MATRIX: the fixed, real tool allowlist (9 OBSERVE-level names)
│   ├── knowledge/
│   │   ├── redaction.py      # Real secret redaction, ported from HYDRA-UMC-OPS-AGENT
│   │   └── trust.py          # UntrustedText + build_tool_request_from_model_output(): the injection-defense boundary
│   ├── orchestrator/          # Fase 3 - all 9 real OBSERVE-level tool handlers, complete
│   │   ├── allowlist.py      # OrchestratorConfig: symbolic-name allow-list a handler resolves against, never a raw path/host/port
│   │   └── dispatch.py       # dispatch_tool_request(): runs a validated ToolRequest for real, returns a real ToolResult
│   ├── contracts.py           # Real, stdlib-only validator for the five minimal contracts
│   └── cli.py                 # contracts validate subcommand + --version
├── contracts/                 # Normative JSON Schema files (draft 2020-12) for the five contracts
├── tests/
│   ├── unit/                  # Real tests for every module above
│   ├── adversarial/           # test_injection_defense.py - Fase 0's own literal exit criterion, extended for Fase 3's own allow-list defense
│   └── fixtures/              # valid/invalid JSON fixtures for each contract
├── docs/
│   ├── ARCHITECTURE.md        # Purpose, five pieces (target design), target architecture, ecosystem relationships
│   ├── SECURITY_MODEL.md      # The six risk levels, data/secrets rules, injection defense
│   ├── CLI_REFERENCE.md       # contracts validate, flags, exit codes
│   └── CONTRACTS.md           # The real field-by-field shape of all five contracts
├── images/                    # Media and app icons
├── build.sh / build.bat       # venv + editable install + compile-check + tests
├── build-test.sh / .bat       # Non-mutating build validation only
├── run.sh / run.bat           # Forwards a real CLI command
├── bump_version.py            # Ecosystem-wide odometer bump (pyproject.toml + __init__.py)
└── bump_manifest_version.py   # Syncs hydra-umc.project.json's version to the native one (--sync)
```

## ⚙️ BUILD & RUN GUIDE

```bash
chmod +x build.sh   # one-time
./build.sh          # creates .venv, pip install -e ".[dev]", compile-checks + tests
./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
./run.sh --version
```

On Windows: `build.bat`, then `run.bat contracts validate ...` /
`run.bat --version`. `build-test.sh`/`.bat` performs the same
non-mutating Python-syntax compile check this project's own CI workflow
performs, without touching the project version or CHANGELOG - it does
NOT run the test suite itself; run `./build.sh`/`build.bat` (or
`pytest tests/` directly) for the full local test suite.

**Troubleshooting**

- `contracts validate` exits `1` with `INVALID: ...`: read the message -
  it names the exact field and reason, not just that something failed.
  Check [docs/CONTRACTS.md](docs/CONTRACTS.md) for the real, expected
  shape of each of the five contracts.
- A test in `tests/adversarial/` fails: this is Fase 0's own literal exit
  criterion - treat any failure there as a real regression in the
  injection-defense boundary, never as a test to relax.

## 🚀 ROADMAP

This version ships Fase 0 and part of Fase 3. What remains, in phase order:

- **Fase 1 - Retrievable knowledge.** A local, versioned index of
  approved documentation, manifests, contracts and runbooks - never
  trained blindly on the whole disk.
- **Fase 2 - Local inference engine.** A small LLM compatible with
  Hailo-10H (candidates: Qwen2.5-1.5B-Instruct, Qwen2.5-Coder-1.5B,
  Qwen3-1.7B-Instruct), chosen only once real Hailo compatibility,
  latency, language quality, power draw and license are verified.
- **Fase 3 - Tool orchestrator (complete: 9 of 9 tools).** Deterministic
  code wiring every real `OBSERVE`-level tool handler to
  `TOOL_MATRIX`, with policy enforcement on every call. `service.status`,
  `storage.usage`, `network.port_status`, `network.connectivity`,
  `system.temperature`, `manifest.read`, `logs.read`, `process.list` and
  `update.pending` are all real now (`orchestrator/dispatch.py`).
- **Fase 4 - Proposals and evidence.** Real `MaintenanceProposal` and
  `EvidenceBundle` generation, escalating toward HYDRA-UMC-DEV-SERVER's
  own future Developer Node role.
- **Fase 5 - User interface.** A local API integrated into
  HYDRA-UMC-SERVER/Studio, then a CLI, then voice - never bypassing the
  policy and confirmation boundaries Fase 0 already establishes.

Fases 1, 2, 4 and 5 do not exist in this repository yet, and Fase 3
itself is only partially done - see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for what each phase is
scoped to include and explicitly exclude, and
[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) for the security
invariants every phase must keep honoring.

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Directly Related**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — this project's own parent: the integration hub for the Hailo-10 cognitive pipeline this technician's future inference engine will run on.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — owns the maintenance-incident lifecycle (evidence, diagnosis, human-approved change, canary deploy, verification); this technician's own `knowledge/redaction.py` is a direct port of its already-tested `log_redaction.py`, and a future phase escalates real evidence packages toward it, never bypassing its own approval flow.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — the future Developer Node a later phase sends a real `EvidenceBundle` to for study, testing and a reviewed patch - never a direct, automatic patch channel.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — will define the shared, versioned contracts this project's own local `contracts/*.schema.json` are meant to reconcile with, once they exist there too.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — the future authenticated entry point that will host this technician's own endpoint, sessions, roles and audit trail.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the physical robot-arm motherboard: CM5 host + dual-core STM32H745, orchestrating up to 8 tool arms over CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproducible Raspberry Pi OS product layer for the CM5: read-only agent, validated config/profiles, WiFi first-contact provisioning.

*Core Backend & Clients*
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — web control dashboard with real-time multi-robot 3D visualization.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop (PySide6) swarm command center for multiple servers at once.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor that pushes finished models into STUDIO's own catalog.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a real VDA 5050 MQTT publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with real GRBL status/control-byte access.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a real Boston Dynamics Spot command sender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell safety coordinator reading 3 real key/enclosure/interlock GPIO safeguards.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — safety coordinator with a real, lazily-imported rclpy ROS 2 transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a real MAVLink command sender.

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — real Position-Based Visual Servoing correction law, safety-gated on upstream zone state.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — real zone-breach checking and E-STOP requesting, with calibration-freshness enforcement.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.

*Orchestration & Swarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — a real gRPC-based fleet health watchdog with its own retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — integration hub for the digital-twin engine, with a real version-compatibility sync contract.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — real hardware-in-the-loop safety interlock routing commands between simulation and real hardware.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — real forward kinematics and joint-limit validation over a real URDF subset.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — real procedural 2D scene generator with YOLO/COCO annotation export.

*Data & Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — real sqlite3-backed time-series store with a real ingest/query HTTP API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — real FFT + statistical baseline anomaly detector with drift monitoring.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — real OEE/availability calculation over DATALAKE history, with reproducible CSV export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — real CAN/WebSocket ingestion pipeline into DATALAKE, with sequence deduplication.

*Industrial Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — integration hub relaying to industrial protocols, with a real command allowlist/backpressure layer.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — real OPC-UA address space, verified with a real binary-protocol client session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — real MQTT broker with optional per-client authentication and topic ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — real MTConnect `/probe` and `/current` XML endpoints with degraded-mode output.

*Complementary Tools*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart Summaries and Anomaly Highlighting panels over DATALAKE/ANOMALY-DETECTOR, with an honest statistical fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — fleet CLI with a real, stable exit-code contract, a genuine live client of HYDRA-UMC-SERVER's own API.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with real haptic alerts and a paired-phone voice relay.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — external adapter capability catalog, GET-only by design.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — builds a fresh CM5 image from source, another "Ecosystem Operations" sibling.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administrative desktop tool that discovers, clones and updates every repo in this ecosystem.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.

---

## 📚 Documentation & Community

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — purpose, the five target pieces, target architecture, and ecosystem relationships.
- **[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)** — the six risk levels, data/secrets rules, and the real, tested injection-defense boundary.
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — every subcommand, its flags, and the exit-code contract.
- **[docs/CONTRACTS.md](docs/CONTRACTS.md)** — the real field-by-field shape of all five contracts.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — tech stack and coding guidelines for a pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — the standards of behavior expected in this community.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability, and this project's own real security focus areas.
- **[SUPPORT.md](SUPPORT.md)** — where to ask questions and report bugs.

## 👤 AUTHOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

GPL-3.0 (software) / CC BY-SA 4.0 (documentation) - see [LICENSE.md](LICENSE.md).
