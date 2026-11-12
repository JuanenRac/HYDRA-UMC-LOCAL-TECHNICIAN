# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/cli_extra.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Command line of the four optional features: the outbox transport, the runbook rules, the signed approvals and the snapshot.

Every command here reads its switch from the configuration file and is refused while the switch is off. None of them runs a step
of a proposal: the runbook engine proposes, the approval commands only sign and verify, and the transport only sends evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import assistant
from .escalation.evidence import EvidenceAssemblyError, verify_bundle
from .escalation.outbox import EscalationOutbox
from .escalation.snapshot import SnapshotError, take_snapshot
from .escalation.transport import TransportError, send_pending
from .policy import approvals
from .policy.execution_mode import ExecutionMode, decide
from .policy.risk_levels import RiskLevel
from .rules import runbook as runbooks
from .settings import SettingsError, load_settings

EXIT_ERROR = 1
EXIT_REFUSED = 2

_ERRORS = (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, json.JSONDecodeError)


def _refuse(message: str) -> int:
    print(f"REFUSED: {message}", file=sys.stderr)
    return EXIT_REFUSED


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cmd_queue(args: argparse.Namespace) -> int:
    try:
        bundle = _read_json(args.bundle)
        verify_bundle(bundle)
        escalation_id = args.id or f"esc-{bundle['checksum'][:16]}"
        answer = EscalationOutbox(Path(args.outbox)).enqueue(escalation_id, bundle)
    except Exception as error:  # noqa: BLE001 - one line for the operator, never a traceback
        return _refuse(str(error))
    print(f"{answer.upper()}: {escalation_id}")
    return 0


def _cmd_send(args: argparse.Namespace) -> int:
    try:
        settings = load_settings(args.config)
        sent = send_pending(EscalationOutbox(Path(args.outbox)), settings.transport)
        left = len(EscalationOutbox(Path(args.outbox)).pending())
    except (TransportError, SettingsError) + _ERRORS as error:
        return _refuse(str(error))
    print(f"SENT: {sent} confirmed, {left} still queued")
    return 0 if left == 0 else EXIT_ERROR


def _cmd_runbook_check(args: argparse.Namespace) -> int:
    try:
        found = runbooks.load_runbooks(Path(args.directory))
    except (runbooks.RunbookError,) + _ERRORS as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return EXIT_ERROR
    print(f"VALID: {len(found)} runbook(s)")
    return 0


def _cmd_runbook_run(args: argparse.Namespace) -> int:
    try:
        settings = load_settings(args.config)
        if not settings.runbooks.enabled:
            return _refuse("the runbook rules are closed: set runbooks.enabled to true in the configuration file")
        results: dict[str, dict[str, Any]] = {}
        for spec in args.result:
            tool, sep, path = spec.partition("=")
            if not sep:
                return _refuse(f"--result must be tool.name=path/to/result.json, got {spec!r}")
            results[tool] = _read_json(path)
        found = runbooks.load_runbooks(Path(settings.runbooks.directory))
        matches = runbooks.evaluate(found, results)
        proposals = {m.runbook.runbook_id: runbooks.build_proposal(m, results, settings.runbooks.language) for m in matches}
    except (runbooks.RunbookError, SettingsError) + _ERRORS as error:
        return _refuse(str(error))
    output = {"matched": sorted(proposals), "proposals": proposals}
    text = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"RUNBOOKS: {len(proposals)} proposal(s) -> {args.output}")
    else:
        print(text)
    return 0


def _cmd_snapshot(args: argparse.Namespace) -> int:
    from .cli import _load_config, _with_audit

    try:
        settings = load_settings(args.config)
        config = _with_audit(_load_config(args.config), args.audit_log)
        path, changes = take_snapshot(config, settings.snapshot)
    except (SnapshotError, SettingsError) + _ERRORS as error:
        return _refuse(str(error))
    print(f"SNAPSHOT -> {path}")
    for line in changes:
        print(f"DRIFT: {line}")
    print(f"DRIFT_COUNT={len(changes)}")
    return 0


def _approval_settings(config: str | None) -> Any:
    settings = load_settings(config).approvals
    if not settings.enabled:
        raise approvals.ApprovalError("signed approvals are closed: set approvals.enabled to true in the configuration file")
    return settings


def _cmd_keygen(args: argparse.Namespace) -> int:
    try:
        print_fp = approvals.generate_keypair(Path(args.private), Path(args.public), args.alias)
    except (approvals.ApprovalError,) + _ERRORS as error:
        return _refuse(str(error))
    print(f"KEYPAIR: private {args.private} (keep it on this machine), public {args.public}\nFINGERPRINT: {print_fp}")
    return 0


def _cmd_trust(args: argparse.Namespace) -> int:
    try:
        settings = _approval_settings(args.config)
        store = approvals.TrustStore.load(Path(settings.trust_store))
        if args.trust_command == "add":
            file_alias, key = approvals.read_public_key_file(Path(args.public_key_file))
            fp = store.add(args.alias or file_alias, key, replace=args.replace)
            print(f"TRUSTED: {args.alias or file_alias} FINGERPRINT: {fp}")
        elif args.trust_command == "remove":
            store.remove(args.alias)
            print(f"REMOVED: {args.alias}")
        elif args.trust_command == "export":
            store.export(args.alias, Path(args.output))
            print(f"EXPORTED: {args.alias} -> {args.output}")
        else:
            for alias in sorted(store.keys):
                print(f"{alias}\t{approvals.fingerprint(store.keys[alias])}")
    except (approvals.ApprovalError, SettingsError) + _ERRORS as error:
        return _refuse(str(error))
    return 0


def _cmd_sign(args: argparse.Namespace) -> int:
    try:
        document = approvals.sign_approval(
            Path(args.private), args.approver, args.action, _read_json(args.proposal), ttl_seconds=args.valid_for)
        Path(args.output).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    except (approvals.ApprovalError,) + _ERRORS as error:
        return _refuse(str(error))
    print(f"APPROVAL -> {args.output}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        settings = _approval_settings(args.config)
        proposal = _read_json(args.proposal)
        record = approvals.verify_approval(
            _read_json(args.approval), proposal, args.action, approvals.TrustStore.load(Path(settings.trust_store)),
            max_validity_seconds=settings.max_validity_seconds, used_nonces=Path(settings.used_nonces) if settings.used_nonces else None)
        decision = decide(ExecutionMode.ASSISTED, RiskLevel.from_wire_name(proposal["risk"]), args.action, record)
    except (approvals.ApprovalError, SettingsError) + _ERRORS as error:
        return _refuse(str(error))
    print(f"APPROVED: {record.approved_by} for {record.action} ({decision.reason})")
    return 0


def _cmd_assistant_ask(args: argparse.Namespace) -> int:
    try:
        settings = load_settings(args.config).assistant
        if args.bundle:
            material = assistant.material_from_bundle(_read_json(args.bundle))
        else:
            material = Path(args.text).read_text(encoding="utf-8")
        answer = assistant.ask(settings, material, args.question)
    except (assistant.AssistantError, SettingsError, EvidenceAssemblyError) + _ERRORS as error:
        return _refuse(str(error))
    lines = [f"ADVISORY (model {answer.model}; nothing was run, nothing was proposed or approved):", answer.text]
    if answer.truncated:
        lines.append("NOTE: the answer was cut to the configured limit.")
    text = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"ADVICE -> {args.output}")
    else:
        print(text)
    return 0


def register(subparsers: Any, esc_sub: Any, tools_sub: Any) -> None:
    asst = subparsers.add_parser("assistant", help="An open, configurable model that writes advice for a person; it proposes and runs nothing (closed unless assistant.enabled).")
    asst_sub = asst.add_subparsers(dest="assistant_command", required=True)
    ask = asst_sub.add_parser("ask", help="Ask the configured endpoint one question about a verified evidence bundle or a text file.")
    ask.add_argument("--config", required=True)
    source = ask.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle", metavar="FILE", help="An assembled EvidenceBundle (its checksum is verified first).")
    source.add_argument("--text", metavar="FILE", help="A text file (redacted before it is sent).")
    ask.add_argument("--question", required=True)
    ask.add_argument("--output", metavar="FILE")
    ask.set_defaults(func=_cmd_assistant_ask)

    queue = esc_sub.add_parser("queue", help="Put an assembled, checksum-verified EvidenceBundle into the outbox.")
    queue.add_argument("--bundle", required=True, metavar="FILE")
    queue.add_argument("--outbox", required=True, metavar="DIR")
    queue.add_argument("--id", help="The escalation id (default: derived from the bundle checksum).")
    queue.set_defaults(func=_cmd_queue)
    send = esc_sub.add_parser("send", help="Send the pending outbox over the configured transport (closed unless transport.enabled).")
    send.add_argument("--outbox", required=True, metavar="DIR")
    send.add_argument("--config", required=True, help="Configuration file with the transport section.")
    send.set_defaults(func=_cmd_send)

    rb = subparsers.add_parser("runbook", help="Deterministic Markdown runbooks that propose maintenance; they never run a step.")
    rb_sub = rb.add_subparsers(dest="runbook_command", required=True)
    check = rb_sub.add_parser("check", help="Validate every runbook of a directory.")
    check.add_argument("directory")
    check.set_defaults(func=_cmd_runbook_check)
    run = rb_sub.add_parser("run", help="Match the runbooks against tool results and build the grounded proposals (closed unless runbooks.enabled).")
    run.add_argument("--config", required=True)
    run.add_argument("--result", action="append", required=True, metavar="TOOL.NAME=PATH")
    run.add_argument("--output", metavar="FILE")
    run.set_defaults(func=_cmd_runbook_run)

    snapshot = tools_sub.add_parser("snapshot", help="Run the health tools once, save a baseline bundle and print the drift (closed unless snapshot.enabled).")
    snapshot.add_argument("--config", required=True)
    snapshot.add_argument("--audit-log")
    snapshot.set_defaults(func=_cmd_snapshot)

    ap = subparsers.add_parser("approval", help="Ed25519 signed approvals and the trust store of public keys (closed unless approvals.enabled).")
    ap_sub = ap.add_subparsers(dest="approval_command", required=True)
    keygen = ap_sub.add_parser("keygen", help="Make a key pair on the approver's machine (the private key stays outside any git tree).")
    keygen.add_argument("--alias", required=True)
    keygen.add_argument("--private", required=True, metavar="FILE")
    keygen.add_argument("--public", required=True, metavar="FILE")
    keygen.set_defaults(func=_cmd_keygen)
    trust = ap_sub.add_parser("trust", help="Manage the public keys this host trusts.")
    trust_sub = trust.add_subparsers(dest="trust_command", required=True)
    for name in ("add", "remove", "export", "list"):
        item = trust_sub.add_parser(name)
        item.add_argument("--config", required=True)
        if name == "add":
            item.add_argument("--public-key-file", required=True, metavar="FILE")
            item.add_argument("--alias")
            item.add_argument("--replace", action="store_true")
        if name in ("remove", "export"):
            item.add_argument("--alias", required=True)
        if name == "export":
            item.add_argument("--output", required=True, metavar="FILE")
        item.set_defaults(func=_cmd_trust)
    sign = ap_sub.add_parser("sign", help="Sign the approval of one action on one proposal (run by the approver).")
    sign.add_argument("--private", required=True, metavar="FILE")
    sign.add_argument("--approver", required=True)
    sign.add_argument("--action", required=True)
    sign.add_argument("--proposal", required=True, metavar="FILE")
    sign.add_argument("--valid-for", type=int, default=300, metavar="SECONDS")
    sign.add_argument("--output", required=True, metavar="FILE")
    sign.set_defaults(func=_cmd_sign)
    verify = ap_sub.add_parser("verify", help="Verify an approval against the trust store and the exact proposal.")
    verify.add_argument("--config", required=True)
    verify.add_argument("--approval", required=True, metavar="FILE")
    verify.add_argument("--proposal", required=True, metavar="FILE")
    verify.add_argument("--action", required=True)
    verify.set_defaults(func=_cmd_verify)
