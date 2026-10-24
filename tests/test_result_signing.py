# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/test_result_signing.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A ToolResult names its tool and, with a local key, is signed; an evidence bundle refuses a result that is not what it claims to be."""
from __future__ import annotations

import copy
import json
import os
import unittest
from unittest import mock

from hydra_umc_local_technician.contracts import ContractValidationError, validate
from hydra_umc_local_technician.escalation.evidence import EvidenceAssemblyError, ObservedResult, assemble_evidence_bundle
from hydra_umc_local_technician.knowledge.trust import ToolRequest
from hydra_umc_local_technician.orchestrator import result_signing
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.orchestrator.dispatch import dispatch_tool_request

KEY = "local-technician-result-key-0123456789"


def request(tool="storage.usage", arguments=None, request_id="req-1"):
    from hydra_umc_local_technician.policy.risk_levels import RiskLevel

    return ToolRequest("1.0", request_id, tool, arguments or {"name": "root"}, RiskLevel.OBSERVE, "test", "test")


def config(tmp_path):
    return OrchestratorConfig(storage_paths={"root": tmp_path})


class ResultSigningTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        self.directory = tempfile.TemporaryDirectory()
        self.config = config(Path(self.directory.name))
        self.addCleanup(self.directory.cleanup)

    def run_with_key(self, key=KEY):
        with mock.patch.dict(os.environ, {result_signing.KEY_VARIABLE: key} if key else {}, clear=False):
            if not key:
                os.environ.pop(result_signing.KEY_VARIABLE, None)
            return dispatch_tool_request(request(), self.config)

    def test_a_result_names_its_tool_and_is_signed_when_a_key_is_configured(self):
        result = self.run_with_key()
        self.assertEqual(result["tool"], "storage.usage")
        self.assertRegex(result["signature"], r"^[0-9a-f]{64}$")
        validate("ToolResult", result)
        result_signing.verify(result, KEY.encode(), expected_tool="storage.usage")

    def test_without_a_key_nothing_is_signed_and_nothing_is_refused(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(result_signing.KEY_VARIABLE, None)
            os.environ.pop(result_signing.KEY_VARIABLE + "_FILE", None)
            result = dispatch_tool_request(request(), self.config)
            self.assertNotIn("signature", result)
            self.assertEqual(result["tool"], "storage.usage")
            bundle = assemble_evidence_bundle([ObservedResult("storage.usage", result)], impact="a disk is filling up")
        self.assertEqual(len(bundle["reproductionSteps"]), 1)

    def test_any_changed_field_breaks_the_signature(self):
        result = self.run_with_key()
        for field, value in (("status", "error"), ("output", {"freeBytes": 1}), ("evidence", "invented"), ("requestId", "other"), ("tool", "logs.read"), ("timestamp", "2030-01-01T00:00:00Z")):
            altered = copy.deepcopy(result)
            altered[field] = value
            with self.assertRaises(result_signing.SignatureError, msg=field):
                result_signing.verify(altered, KEY.encode())
        with self.assertRaises(result_signing.SignatureError):
            result_signing.verify(result, b"another-key-of-sixteen-chars")

    def test_a_bundle_with_a_key_refuses_an_unsigned_a_forged_and_a_mislabelled_result(self):
        result = self.run_with_key()
        with mock.patch.dict(os.environ, {result_signing.KEY_VARIABLE: KEY}):
            ok = assemble_evidence_bundle([ObservedResult("storage.usage", result)], impact="a disk is filling up")
            self.assertTrue(ok["checksum"])

            unsigned = {k: v for k, v in result.items() if k != "signature"}
            with self.assertRaisesRegex(EvidenceAssemblyError, "not signed"):
                assemble_evidence_bundle([ObservedResult("storage.usage", unsigned)], impact="x")

            forged = copy.deepcopy(result)
            forged["output"] = {"freeBytes": 0}
            with self.assertRaisesRegex(EvidenceAssemblyError, "does not verify"):
                assemble_evidence_bundle([ObservedResult("storage.usage", forged)], impact="x")

            with self.assertRaisesRegex(EvidenceAssemblyError, "presented as|not 'logs.read'"):
                assemble_evidence_bundle([ObservedResult("logs.read", result)], impact="x")

    def test_a_result_that_names_another_tool_is_refused_even_without_a_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(result_signing.KEY_VARIABLE, None)
            os.environ.pop(result_signing.KEY_VARIABLE + "_FILE", None)
            result = dispatch_tool_request(request(), self.config)
            with self.assertRaisesRegex(EvidenceAssemblyError, "presented as"):
                assemble_evidence_bundle([ObservedResult("logs.read", result)], impact="x")

    def test_the_key_may_come_from_a_file_and_must_be_long_enough(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key"
            path.write_text(KEY + "\nsecond line ignored\n", encoding="utf-8")
            self.assertEqual(result_signing.result_key({result_signing.KEY_VARIABLE + "_FILE": str(path)}), KEY.encode())
        self.assertIsNone(result_signing.result_key({}))
        self.assertIsNone(result_signing.result_key({result_signing.KEY_VARIABLE + "_FILE": "/no/such/file"}))
        with self.assertRaises(result_signing.SignatureError):
            result_signing.result_key({result_signing.KEY_VARIABLE: "short"})

    def test_the_contract_accepts_the_two_new_fields_and_nothing_else(self):
        result = self.run_with_key()
        validate("ToolResult", result)
        extra = dict(result, other=1)
        with self.assertRaises(ContractValidationError):
            validate("ToolResult", extra)
        bad = dict(result, signature="XYZ")
        with self.assertRaises(ContractValidationError):
            validate("ToolResult", bad)
        # a result made before the fields existed is still valid
        old = {k: v for k, v in result.items() if k not in ("tool", "signature")}
        validate("ToolResult", old)
        self.assertEqual(set(json.loads(json.dumps(old))) | {"tool", "signature"}, set(result))


if __name__ == "__main__":
    unittest.main()
