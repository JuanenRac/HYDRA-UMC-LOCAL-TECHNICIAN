# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real CLI entry point for Fase 0 only: `contracts validate` checks a
JSON payload against one of the five real minimal contracts
(contracts.py). No inference, no RAG, no real tool execution, and no
HYDRA-UMC-SERVER integration exist yet - see README ROADMAP.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .contracts import REQUIRED, ContractValidationError, validate


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hydra-umc-local-technician",
        description="Local, policy-gated AI maintenance technician - Fase 0 only: contract validation.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    contracts = subparsers.add_parser("contracts", help="Contract validation commands.")
    contracts_sub = contracts.add_subparsers(dest="contracts_command", required=True)
    validate_cmd = contracts_sub.add_parser("validate", help="Validate a JSON payload against one of the five real contracts.")
    validate_cmd.add_argument("payload_file", help="Path to a JSON payload.")
    validate_cmd.add_argument("--contract", required=True, choices=sorted(REQUIRED), help="Which contract to validate against.")
    validate_cmd.set_defaults(func=_cmd_contracts_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
