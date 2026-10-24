# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Real CLI entry point.

`contracts validate` (Fase 0) checks a JSON payload against one of the
five real minimal contracts (contracts.py). `tools list`/`tools call`
and `escalation evidence`/`escalation propose` (Fase 5's own first real
slice) expose exactly the same real, already-tested code path every unit
test already exercises - `dispatch_tool_request()`,
`assemble_evidence_bundle()`, `propose_maintenance()` - through a real
command line, never a new one. This CLI adds no authority of its own:
every policy/allow-list/grounding check those functions already enforce
still applies unchanged, and `tools call` can still only ever reach an
OBSERVE-level tool (nothing above OBSERVE is implemented anywhere in
this codebase). No inference, no RAG, and no HYDRA-UMC-SERVER
integration exist yet - see README's own ROADMAP.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from . import __version__
from .contracts import REQUIRED, ContractValidationError, validate
from .escalation.evidence import EvidenceAssemblyError, ObservedResult, assemble_evidence_bundle, verify_bundle
from .escalation.proposal import ProposalError, propose_maintenance
from .knowledge.trust import ToolCallRefused, build_tool_request_from_model_output
from .orchestrator.allowlist import OrchestratorConfig, default_config
from .orchestrator.audit import DEFAULT_BACKUPS, DEFAULT_MAX_BYTES, AuditLog, audit_log_from
from .orchestrator.dispatch import ToolDispatchError, dispatch_tool_request
from .policy.risk_levels import RiskLevel
from .policy.tool_matrix import TOOL_MATRIX


# Exit codes: 0 done; 1 the work ran and its result is an error (a tool status that is not ok, an invalid contract, a journal chain that is
# broken); 2 the request was refused before anything ran (an argument, a configuration, a policy or a grounding check said no).
EXIT_ERROR = 1
EXIT_REFUSED = 2


def _write_output(path: str, text: str) -> None:
    """Writes `text` to `path` without ever leaving a half-written file where a reader might pick it up."""
    target = Path(path)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(text + "\n", encoding="utf-8")
    os.replace(temporary, target)


def _cmd_contracts_validate(args: argparse.Namespace) -> int:
    path = Path(args.payload_file)
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"INVALID: could not read {path}: {exc}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"INVALID: {path} is not valid JSON: {exc}", file=sys.stderr)
        return 1
    try:
        validate(args.contract, payload)
    except ContractValidationError as exc:
        print(f"INVALID: {path} ({args.contract}): {exc}", file=sys.stderr)
        return 1
    print(f"VALID: {path} ({args.contract})")
    return 0


def _load_config(config_path: str | None) -> OrchestratorConfig:
    """Loads a real `OrchestratorConfig` from a JSON file (same field
    names as the dataclass, camelCase on the wire - see
    orchestrator/allowlist.py's own field comments for what each one may
    ever point at), or `default_config()` - the real, documented CM5
    defaults - when no `--config` is given. There is deliberately no way
    to name a raw path/host/port on the command line itself: every
    symbolic name this CLI can ever resolve still has to already be in
    this config, exactly the same allow-list boundary every test already
    exercises."""
    if config_path is None:
        return default_config()
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    _validate_config_shape(raw)
    return OrchestratorConfig(
        storage_paths={name: Path(value) for name, value in raw.get("storagePaths", {}).items()},
        ports={name: (value[0], value[1]) for name, value in raw.get("ports", {}).items()},
        connectivity_targets=dict(raw.get("connectivityTargets", {})),
        systemd_units=tuple(raw.get("systemdUnits", ())),
        ecosystem_root=Path(raw["ecosystemRoot"]) if raw.get("ecosystemRoot") else None,
        log_sources={name: Path(value) for name, value in raw.get("logSources", {}).items()},
        process_patterns=dict(raw.get("processPatterns", {})),
        knowledge_sources={name: Path(value) for name, value in raw.get("knowledgeSources", {}).items()},
        audit_log=_audit_from_config(raw.get("auditLog")),
    )


def _with_audit(config: OrchestratorConfig, path: str | None) -> OrchestratorConfig:
    """The journal named by --audit-log or the environment, unless the configuration file already set one."""
    if config.audit_log is not None:
        return config
    journal = audit_log_from(path, dict(os.environ))
    return config if journal is None else dataclasses.replace(config, audit_log=journal)


def _cmd_audit_verify(args: argparse.Namespace) -> int:
    ok, summary = AuditLog(args.path).verify()
    print(("AUDIT_CHAIN=PASS " if ok else "AUDIT_CHAIN=FAIL ") + summary)
    return 0 if ok else 1


def _audit_from_config(section: object) -> AuditLog | None:
    """`"auditLog": {"path": "/var/lib/.../audit.jsonl", "maxBytes": 5242880, "backups": 5}`; absent means off."""
    if section is None:
        return None
    return AuditLog(section["path"], max_bytes=section.get("maxBytes", DEFAULT_MAX_BYTES), backups=section.get("backups", DEFAULT_BACKUPS))


_CONFIG_KEYS = {
    "storagePaths", "ports", "connectivityTargets", "systemdUnits", "ecosystemRoot",
    "logSources", "processPatterns", "knowledgeSources", "auditLog",
}


def _validate_config_shape(raw: object) -> None:
    """A --config file must have the documented shape: known keys, string lists
    where lists are expected, absolute paths, ports 1-65535. A typo or a bare
    string ("systemdUnits": "hydra-umc-server" used to become a tuple of single
    letters) is a one-line error, never a silently different allow-list."""
    if not isinstance(raw, dict):
        raise ValueError("the config must be a JSON object")
    unknown = sorted(set(raw) - _CONFIG_KEYS)
    if unknown:
        raise ValueError(f"unknown config key(s): {', '.join(unknown)}")
    audit = raw.get("auditLog")
    if audit is not None:
        if not isinstance(audit, dict) or not isinstance(audit.get("path"), str) or not audit["path"]:
            raise ValueError('"auditLog" must be an object with a "path"')
        unknown_audit = sorted(set(audit) - {"path", "maxBytes", "backups"})
        if unknown_audit:
            raise ValueError(f"unknown auditLog key(s): {', '.join(unknown_audit)}")
    units = raw.get("systemdUnits", [])
    if not isinstance(units, list) or not all(isinstance(unit, str) and unit for unit in units):
        raise ValueError('"systemdUnits" must be a list of unit names')
    for key in ("storagePaths", "logSources", "knowledgeSources"):
        mapping = raw.get(key, {})
        if not isinstance(mapping, dict):
            raise ValueError(f'"{key}" must be an object of name -> absolute path')
        for name, value in mapping.items():
            if not isinstance(value, str) or not Path(value).is_absolute():
                raise ValueError(f'"{key}.{name}" must be an absolute path')
    root = raw.get("ecosystemRoot")
    if root is not None and (not isinstance(root, str) or not Path(root).is_absolute()):
        raise ValueError('"ecosystemRoot" must be an absolute path')
    ports = raw.get("ports", {})
    if not isinstance(ports, dict):
        raise ValueError('"ports" must be an object of name -> [host, port]')
    for name, value in ports.items():
        if (
            not isinstance(value, list) or len(value) != 2 or not isinstance(value[0], str)
            or isinstance(value[1], bool) or not isinstance(value[1], int) or not 1 <= value[1] <= 65535
        ):
            raise ValueError(f'"ports.{name}" must be [host, port] with a port from 1 to 65535')
    for key in ("connectivityTargets", "processPatterns"):
        mapping = raw.get(key, {})
        if not isinstance(mapping, dict) or not all(isinstance(v, str) for v in mapping.values()):
            raise ValueError(f'"{key}" must be an object of name -> string')


def _cmd_tools_list(args: argparse.Namespace) -> int:
    for name, descriptor in sorted(TOOL_MATRIX.items()):
        status = "implemented" if descriptor.implemented else "not implemented"
        print(f"{name}\t{descriptor.risk_level.wire_name}\t{status}\t{descriptor.description}")
    return 0


def _parse_argument_value(raw: str) -> Any:
    """`--arg name=value`'s own `value` half - tried as real JSON first
    (so `--arg topK=5` becomes the real int `5`, `--arg foo=true` the
    real bool `True`, matching what a tool handler's own `arguments`
    dict actually expects), falling back to the literal string when it
    is not valid JSON (so `--arg project=HYDRA-UMC-EXAMPLE` stays a
    plain string without needing to be quoted twice)."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _cmd_tools_call(args: argparse.Namespace) -> int:
    try:
        config = _with_audit(_load_config(args.config), args.audit_log)
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        # A config file that is missing, not JSON, or shaped wrongly is an
        # operator mistake to report in one line, not a traceback.
        print(f"REFUSED: invalid --config {args.config}: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    arguments: dict[str, Any] = {}
    for spec in args.arg or ():
        name, sep, value = spec.partition("=")
        if not sep:
            print(f"REFUSED: --arg must be name=value, got {spec!r}", file=sys.stderr)
            return EXIT_REFUSED
        arguments[name] = _parse_argument_value(value)

    try:
        request = build_tool_request_from_model_output(
            request_id=str(uuid.uuid4()), tool=args.tool, arguments=arguments,
            actor=args.actor, reason=args.reason,
        )
        result = dispatch_tool_request(request, config)
    except (ToolCallRefused, ToolDispatchError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        try:
            _write_output(args.output, text)
        except OSError as exc:
            print(f"REFUSED: cannot write --output {args.output}: {exc}", file=sys.stderr)
            return EXIT_REFUSED
        print(f"{result['status'].upper()}: {args.tool} -> {args.output}")
    else:
        print(text)
    return 0 if result["status"] == "ok" else EXIT_ERROR


def _load_observed_results(specs: list[str]) -> list[ObservedResult]:
    """`--result tool.name=path/to/result.json`'s own real parsing - the
    same real `ToolResult` a prior `tools call ... > result.json` already
    produced and this repo's own dispatch.py already validated once;
    `escalation.evidence.assemble_evidence_bundle()` re-validates it
    again on its own before trusting it further (see that module's own
    docstring for why)."""
    observed = []
    for spec in specs:
        tool_name, sep, path = spec.partition("=")
        if not sep:
            raise ValueError(f"--result must be tool.name=path/to/result.json, got {spec!r}")
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        observed.append(ObservedResult(tool_name, result))
    return observed


def _cmd_escalation_evidence(args: argparse.Namespace) -> int:
    try:
        observed = _load_observed_results(args.result)
        bundle = assemble_evidence_bundle(
            observed, impact=args.impact, local_validation_result=args.local_validation,
            actions_attempted=args.action_attempted or None, failed_tests=args.failed_test or None,
        )
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError, EvidenceAssemblyError, ContractValidationError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    text = json.dumps(bundle, indent=2, ensure_ascii=False)
    if args.output:
        try:
            _write_output(args.output, text)
        except OSError as exc:
            print(f"REFUSED: cannot write --output {args.output}: {exc}", file=sys.stderr)
            return EXIT_REFUSED
        print(f"EVIDENCE_BUNDLE -> {args.output}")
    else:
        print(text)
    return 0


def _cmd_escalation_propose(args: argparse.Namespace) -> int:
    try:
        if not args.result and not args.from_bundle:
            raise ValueError("give the tool results the diagnosis rests on (--result) or an assembled evidence bundle (--from-bundle)")
        evidence_pool = _load_observed_results(args.result or [])
        bundle_evidence = verify_bundle(json.loads(Path(args.from_bundle).read_text(encoding="utf-8"))) if args.from_bundle else None
        risk = RiskLevel.from_wire_name(args.risk)
        proposal = propose_maintenance(
            diagnosis=args.diagnosis, cited_evidence=args.cited_evidence, evidence_pool=evidence_pool,
            scope=args.scope, risk=risk, steps=args.step, rollback=args.rollback,
            pre_checks=args.pre_check or None, expected_changes=args.expected_change or None,
            explicit_limits=args.explicit_limit or None, bundle_evidence=bundle_evidence,
        )
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError, ProposalError, EvidenceAssemblyError, ContractValidationError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    text = json.dumps(proposal, indent=2, ensure_ascii=False)
    if args.output:
        try:
            _write_output(args.output, text)
        except OSError as exc:
            print(f"REFUSED: cannot write --output {args.output}: {exc}", file=sys.stderr)
            return EXIT_REFUSED
        print(f"MAINTENANCE_PROPOSAL -> {args.output}")
    else:
        print(text)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Fase 5: the read-only local API and web page (webapi.py). It answers GET
    only, binds to loopback unless told otherwise, and then needs a token."""
    from .webapi import ApiConfigError, TechnicianServer, read_api_token

    try:
        config = _with_audit(_load_config(args.config), args.audit_log)
        token = read_api_token(args.token_file, dict(os.environ))
        server = TechnicianServer((args.host, args.port), data_dir=Path(args.data_dir), config=config, token=token)
    except (ApiConfigError, OSError, OverflowError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        print(f"REFUSED: cannot start the read-only API: {exc}", file=sys.stderr)
        return 1
    shown = f"[{args.host}]" if ":" in args.host else args.host
    print(f"Read-only API and web page on http://{shown}:{server.server_address[1]}/ (GET only; token {'required' if token else 'not set'}).")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hydra-umc-local-technician",
        description="Local, policy-gated AI maintenance technician.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    contracts = subparsers.add_parser("contracts", help="Contract validation commands.")
    contracts_sub = contracts.add_subparsers(dest="contracts_command", required=True)
    validate_cmd = contracts_sub.add_parser("validate", help="Validate a JSON payload against one of the five real contracts.")
    validate_cmd.add_argument("payload_file", help="Path to a JSON payload.")
    validate_cmd.add_argument("--contract", required=True, choices=sorted(REQUIRED), help="Which contract to validate against.")
    validate_cmd.set_defaults(func=_cmd_contracts_validate)

    tools = subparsers.add_parser("tools", help="Fase 5: real OBSERVE-level tool commands.")
    tools_sub = tools.add_subparsers(dest="tools_command", required=True)

    list_cmd = tools_sub.add_parser("list", help="List every real, registered tool and its implementation status.")
    list_cmd.set_defaults(func=_cmd_tools_list)

    call_cmd = tools_sub.add_parser("call", help="Call a real, registered OBSERVE-level tool for real and print its ToolResult.")
    call_cmd.add_argument("tool", help="A tool name already registered in policy/tool_matrix.py, e.g. service.status.")
    call_cmd.add_argument("--arg", action="append", metavar="NAME=VALUE", help="One tool argument (repeatable), e.g. --arg name=server_http.")
    call_cmd.add_argument("--actor", default="cli", help="Who is making this call - recorded on the real ToolRequest.")
    call_cmd.add_argument("--reason", default="manual CLI call", help="Why - recorded on the real ToolRequest.")
    call_cmd.add_argument("--config", help="Path to a JSON OrchestratorConfig file; defaults to default_config() (the documented CM5 defaults) when omitted.")
    call_cmd.add_argument("--audit-log", help="Append-only JSONL journal of every request and its outcome (or HYDRA_UMC_LOCAL_TECHNICIAN_AUDIT_LOG, or auditLog in --config). When on, a request that cannot be recorded is not run.")
    call_cmd.add_argument("--output", metavar="FILE", help="Write the ToolResult to FILE (replaced whole, never half written) instead of standard output, ready for --result of the escalation commands. Exit codes: 0 ok, 1 the tool answered with an error, 2 refused before anything ran.")
    call_cmd.set_defaults(func=_cmd_tools_call)

    escalation = subparsers.add_parser("escalation", help="Fase 4/5: real EvidenceBundle assembly and MaintenanceProposal construction.")
    escalation_sub = escalation.add_subparsers(dest="escalation_command", required=True)

    evidence_cmd = escalation_sub.add_parser("evidence", help="Assemble a real EvidenceBundle from already-produced ToolResult files.")
    evidence_cmd.add_argument("--result", action="append", required=True, metavar="TOOL.NAME=PATH", help="One real ToolResult JSON file (repeatable), e.g. --result service.status=result.json.")
    evidence_cmd.add_argument("--impact", required=True, help="Real, honest description of the impact - this module never invents it.")
    evidence_cmd.add_argument("--local-validation", help="What local validation (if any) already showed.")
    evidence_cmd.add_argument("--action-attempted", action="append", help="Something already tried (repeatable).")
    evidence_cmd.add_argument("--failed-test", action="append", help="A real test that failed (repeatable).")
    evidence_cmd.add_argument("--output", metavar="FILE", help="Write the bundle to FILE instead of standard output, ready for --from-bundle.")
    evidence_cmd.set_defaults(func=_cmd_escalation_evidence)

    propose_cmd = escalation_sub.add_parser("propose", help="Build a real MaintenanceProposal, grounded against already-produced ToolResult files.")
    propose_cmd.add_argument("--diagnosis", required=True, help="What you believe is wrong - never generated by this CLI.")
    propose_cmd.add_argument("--cited-evidence", action="append", required=True, help="Must exactly match a real ToolResult's own evidence field (repeatable).")
    propose_cmd.add_argument("--result", action="append", metavar="TOOL.NAME=PATH", help="One real ToolResult JSON file backing --cited-evidence (repeatable).")
    propose_cmd.add_argument("--from-bundle", metavar="FILE", help="An EvidenceBundle assembled by 'escalation evidence' (its checksum is verified): its reproduction steps are the evidence --cited-evidence may cite, so the tool result files are not needed again. Give this, --result, or both.")
    propose_cmd.add_argument("--output", metavar="FILE", help="Write the proposal to FILE instead of standard output.")
    propose_cmd.add_argument("--scope", required=True, help="What this proposal touches.")
    propose_cmd.add_argument("--risk", required=True, choices=[level.wire_name for level in RiskLevel], help="The proposal's own declared risk level.")
    propose_cmd.add_argument("--step", action="append", required=True, help="One real, ordered step (repeatable).")
    propose_cmd.add_argument("--rollback", required=True, help="How to undo it.")
    propose_cmd.add_argument("--pre-check", action="append", help="A check to run before applying any step (repeatable).")
    propose_cmd.add_argument("--expected-change", action="append", help="What should differ afterward (repeatable).")
    propose_cmd.add_argument("--explicit-limit", action="append", help="What this proposal explicitly does NOT cover (repeatable).")
    propose_cmd.set_defaults(func=_cmd_escalation_propose)

    serve_cmd = subparsers.add_parser("serve", allow_abbrev=False, help="Fase 5: serve the read-only local API and web page (GET only; loopback unless a token is set).")
    serve_cmd.add_argument("--host", default="127.0.0.1", help="Address to bind (default 127.0.0.1). Any non-loopback address requires a token.")
    serve_cmd.add_argument("--port", type=int, default=8780, help="Port (default 8780; 0 picks a free one).")
    serve_cmd.add_argument("--data-dir", required=True, help="Directory holding tool-results/, evidence/ and proposals/ (JSON files saved from the CLI's output).")
    serve_cmd.add_argument("--config", help="Path to a JSON OrchestratorConfig file (manifests and knowledge sources); defaults to default_config().")
    serve_cmd.add_argument("--token-file", help="File holding the bearer token (at least 24 characters); otherwise HYDRA_UMC_LOCAL_TECHNICIAN_TOKEN. Never taken from the command line.")
    serve_cmd.add_argument("--audit-log", help="Append-only JSONL journal of the tool requests the API makes (or HYDRA_UMC_LOCAL_TECHNICIAN_AUDIT_LOG).")
    serve_cmd.set_defaults(func=_cmd_serve)

    audit_cmd = subparsers.add_parser("audit-verify", allow_abbrev=False, help="Check that the hash chain of an audit journal (and its rotated files) is unbroken.")
    audit_cmd.add_argument("path", help="The audit journal, e.g. /var/lib/hydra-umc/local-technician/audit.jsonl.")
    audit_cmd.set_defaults(func=_cmd_audit_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
