# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_contracts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import json
import unittest
from pathlib import Path

from hydra_umc_local_technician.contracts import ContractValidationError, validate

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

_CONTRACTS = (
    ("ToolRequest", "tool_request"),
    ("ToolResult", "tool_result"),
    ("MaintenanceProposal", "maintenance_proposal"),
    ("EvidenceBundle", "evidence_bundle"),
    ("PatchVerificationReport", "patch_verification_report"),
)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ContractFixtureTests(unittest.TestCase):
    def test_every_valid_fixture_passes(self):
        for contract_name, file_stem in _CONTRACTS:
            with self.subTest(contract=contract_name):
                payload = _load(f"{file_stem}.valid.json")
                validate(contract_name, payload)  # must not raise

    def test_every_invalid_fixture_is_rejected(self):
        for contract_name, file_stem in _CONTRACTS:
            with self.subTest(contract=contract_name):
                payload = _load(f"{file_stem}.invalid.json")
                with self.assertRaises(ContractValidationError):
                    validate(contract_name, payload)

    def test_unknown_contract_name_is_rejected(self):
        with self.assertRaises(ContractValidationError):
            validate("NotARealContract", {})

    def test_non_object_payload_is_rejected(self):
        with self.assertRaises(ContractValidationError):
            validate("ToolRequest", [1, 2, 3])  # type: ignore[arg-type]

    def test_a_missing_required_field_is_named_in_the_error(self):
        payload = _load("tool_request.valid.json")
        del payload["reason"]
        with self.assertRaises(ContractValidationError) as ctx:
            validate("ToolRequest", payload)
        self.assertIn("reason", str(ctx.exception))

    # regressions: the Python validator used to accept several
    # values its own normative contracts/*.schema.json already declares
    # invalid, because "type": "string"/format constraints on list items
    # and the "date-time" format were never actually enforced here.
    def test_a_non_string_list_element_is_rejected(self):
        payload = _load("maintenance_proposal.valid.json")
        payload["steps"] = payload["steps"] + [42]
        with self.assertRaises(ContractValidationError) as ctx:
            validate("MaintenanceProposal", payload)
        self.assertIn("steps[", str(ctx.exception))

    def test_a_non_finite_duration_ms_is_rejected(self):
        payload = _load("tool_result.valid.json")
        payload["durationMs"] = float("nan")
        with self.assertRaises(ContractValidationError):
            validate("ToolResult", payload)

    def test_an_infinite_duration_ms_is_rejected(self):
        payload = _load("tool_result.valid.json")
        payload["durationMs"] = float("inf")
        with self.assertRaises(ContractValidationError):
            validate("ToolResult", payload)

    def test_a_non_iso_timestamp_is_rejected(self):
        payload = _load("tool_result.valid.json")
        payload["timestamp"] = "not a real date"
        with self.assertRaises(ContractValidationError) as ctx:
            validate("ToolResult", payload)
        self.assertIn("timestamp", str(ctx.exception))

    def test_a_non_iso_date_is_rejected_in_evidence_bundle(self):
        payload = _load("evidence_bundle.valid.json")
        payload["date"] = "yesterday"
        with self.assertRaises(ContractValidationError) as ctx:
            validate("EvidenceBundle", payload)
        self.assertIn("date", str(ctx.exception))

    def test_an_unexpected_extra_field_is_rejected(self):
        # Real defense-in-depth: additionalProperties=false in the schema
        # files (contracts/*.schema.json) means a smuggled extra field
        # (e.g. a retrieved document trying to add its own "override"
        # key) is refused, not silently carried through.
        payload = _load("tool_request.valid.json")
        payload["unexpectedField"] = "should never be allowed through"
        with self.assertRaises(ContractValidationError) as ctx:
            validate("ToolRequest", payload)
        self.assertIn("unexpectedField", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
