# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
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
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from . import __version__
from .contracts import REQUIRED, ContractValidationError, validate
from .escalation.evidence import EvidenceAssemblyError, ObservedResult, assemble_evidence_bundle
from .escalation.proposal import ProposalError, propose_maintenance
from .knowledge.trust import ToolCallRefused, build_tool_request_from_model_output
from .orchestrator.allowlist import OrchestratorConfig, default_config
from .orchestrator.dispatch import ToolDispatchError, dispatch_tool_request
from .policy.risk_levels import RiskLevel
from .policy.tool_matrix import TOOL_MATRIX


def _cmd_contracts_validate(args: argparse.Namespace) -> int:
    path = Path(args.payload_file)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
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
    return OrchestratorConfig(
        storage_paths={name: Path(value) for name, value in raw.get("storagePaths", {}).items()},
        ports={name: (value[0], value[1]) for name, value in raw.get("ports", {}).items()},
        connectivity_targets=dict(raw.get("connectivityTargets", {})),
        systemd_units=tuple(raw.get("systemdUnits", ())),
        ecosystem_root=Path(raw["ecosystemRoot"]) if raw.get("ecosystemRoot") else None,
        log_sources={name: Path(value) for name, value in raw.get("logSources", {}).items()},
        process_patterns=dict(raw.get("processPatterns", {})),
        knowledge_sources={name: Path(value) for name, value in raw.get("knowledgeSources", {}).items()},
    )


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
    config = _load_config(args.config)
    arguments: dict[str, Any] = {}
    for spec in args.arg or ():
        name, sep, value = spec.partition("=")
        if not sep:
            print(f"REFUSED: --arg must be name=value, got {spec!r}", file=sys.stderr)
            return 1
        arguments[name] = _parse_argument_value(value)

    try:
        request = build_tool_request_from_model_output(
            request_id=str(uuid.uuid4()), tool=args.tool, arguments=arguments,
            actor=args.actor, reason=args.reason,
        )
        result = dispatch_tool_request(request, config)
    except (ToolCallRefused, ToolDispatchError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


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
    except (ValueError, OSError, json.JSONDecodeError, EvidenceAssemblyError, ContractValidationError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(bundle, indent=2, ensure_ascii=False))
    return 0


def _cmd_escalation_propose(args: argparse.Namespace) -> int:
    try:
        evidence_pool = _load_observed_results(args.result)
        risk = RiskLevel.from_wire_name(args.risk)
        proposal = propose_maintenance(
            diagnosis=args.diagnosis, cited_evidence=args.cited_evidence, evidence_pool=evidence_pool,
            scope=args.scope, risk=risk, steps=args.step, rollback=args.rollback,
            pre_checks=args.pre_check or None, expected_changes=args.expected_change or None,
            explicit_limits=args.explicit_limit or None,
        )
    except (ValueError, OSError, json.JSONDecodeError, ProposalError, ContractValidationError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(proposal, indent=2, ensure_ascii=False))
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
    call_cmd.set_defaults(func=_cmd_tools_call)

    escalation = subparsers.add_parser("escalation", help="Fase 4/5: real EvidenceBundle assembly and MaintenanceProposal construction.")
    escalation_sub = escalation.add_subparsers(dest="escalation_command", required=True)

    evidence_cmd = escalation_sub.add_parser("evidence", help="Assemble a real EvidenceBundle from already-produced ToolResult files.")
    evidence_cmd.add_argument("--result", action="append", required=True, metavar="TOOL.NAME=PATH", help="One real ToolResult JSON file (repeatable), e.g. --result service.status=result.json.")
    evidence_cmd.add_argument("--impact", required=True, help="Real, honest description of the impact - this module never invents it.")
    evidence_cmd.add_argument("--local-validation", help="What local validation (if any) already showed.")
    evidence_cmd.add_argument("--action-attempted", action="append", help="Something already tried (repeatable).")
    evidence_cmd.add_argument("--failed-test", action="append", help="A real test that failed (repeatable).")
    evidence_cmd.set_defaults(func=_cmd_escalation_evidence)

    propose_cmd = escalation_sub.add_parser("propose", help="Build a real MaintenanceProposal, grounded against already-produced ToolResult files.")
    propose_cmd.add_argument("--diagnosis", required=True, help="What you believe is wrong - never generated by this CLI.")
    propose_cmd.add_argument("--cited-evidence", action="append", required=True, help="Must exactly match a real ToolResult's own evidence field (repeatable).")
    propose_cmd.add_argument("--result", action="append", required=True, metavar="TOOL.NAME=PATH", help="One real ToolResult JSON file backing --cited-evidence (repeatable).")
    propose_cmd.add_argument("--scope", required=True, help="What this proposal touches.")
    propose_cmd.add_argument("--risk", required=True, choices=[level.wire_name for level in RiskLevel], help="The proposal's own declared risk level.")
    propose_cmd.add_argument("--step", action="append", required=True, help="One real, ordered step (repeatable).")
    propose_cmd.add_argument("--rollback", required=True, help="How to undo it.")
    propose_cmd.add_argument("--pre-check", action="append", help="A check to run before applying any step (repeatable).")
    propose_cmd.add_argument("--expected-change", action="append", help="What should differ afterward (repeatable).")
    propose_cmd.add_argument("--explicit-limit", action="append", help="What this proposal explicitly does NOT cover (repeatable).")
    propose_cmd.set_defaults(func=_cmd_escalation_propose)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
