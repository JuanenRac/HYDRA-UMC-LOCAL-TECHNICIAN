# Security Policy 🔒 (HYDRA-UMC-LOCAL-TECHNICIAN)

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.x.x   | ✅ Yes    |

## Reporting a Vulnerability

**CRITICAL: Do not report vulnerabilities through public GitHub issues.**

This project is built, from its very first delivery, around one
non-negotiable limit: the AI never gets authority by generating a
response - policy, permissions and human confirmation decide every
action. If you discover a vulnerability affecting:

- **The injection-defense boundary** (`knowledge/trust.py`) - any way a
  retrieved document (a README, a log line, a commit message) wrapped as
  `UntrustedText` could cause a real `ToolRequest` to be built, or any
  way `build_tool_request_from_model_output()` could be made to accept
  an unregistered or unimplemented tool name. This is the single most
  safety-critical invariant in this delivery.
- **The tool matrix's own allowlist guarantee** (`policy/tool_matrix.py`)
  - any way to invoke a tool name that is not a real key in
  `TOOL_MATRIX`, or any way `lookup_tool()` could return a descriptor for
  a name that was never actually registered.
- **The risk-level policy** (`policy/risk_levels.py`) - any way a
  `RiskLevelPolicy`'s own `can_mutate`/`requires_confirmation` fields
  could be bypassed, or any way `PRIVILEGED_CHANGE`/`PHYSICAL_ACTION`
  could be reached despite both being declared `implemented=False`.
- **Secret redaction** (`knowledge/redaction.py`) - a real secret shape
  (a password, token, SSH key, or credential-bearing URL) that
  `redact_secrets()`/`redact_lines()` fails to catch. Given this
  module is a byte-for-byte port of HYDRA-UMC-OPS-AGENT's own
  already-tested `log_redaction.py`, please also check whether the same
  gap exists there.
- **Contract validation** (`contracts.py`) - a way to make
  `validate()` accept a payload that violates its own normative JSON
  Schema file under `contracts/`, or a way to make the CLI's
  `contracts validate` command execute, evaluate, or otherwise treat
  payload content as anything other than inert JSON data.

**Not yet applicable** - Fase 1 and later (a real inference engine, a RAG
index, real tool execution, HYDRA-UMC-SERVER integration,
`REVERSIBLE_OPERATION` and above) do not exist yet in this delivery.
There is no network-facing service, no model running, and no tool with a
real handler anywhere in this repository yet, so there is nothing there
to have a vulnerability in.

Please report responsibly:

1. **Email**: Send a detailed report to `electrohobby3d@gmail.com`.
2. **Impact**: Describe the attack surface affected and a realistic
   scenario (today's only real attack surface is what a maliciously
   crafted document, log excerpt, or JSON payload could make the
   `contracts validate` CLI command or the injection-defense boundary
   do when exercised directly - there is no remote service to attack).
3. **Response**: Initial acknowledgment within 48 hours.

We follow a coordinated disclosure policy.
