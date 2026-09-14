# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_evidence.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 4's EvidenceBundle half, exercised against real ToolResults - a
real manifest file on disk for manifest.read, a real log file for
logs.read, real dispatch_tool_request() calls, same real-not-mocked
convention test_dispatch.py already established."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.contracts import ContractValidationError, validate
from hydra_umc_local_technician.escalation.evidence import EvidenceAssemblyError, ObservedResult, assemble_evidence_bundle
from hydra_umc_local_technician.knowledge.trust import build_tool_request_from_model_output
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.orchestrator.dispatch import dispatch_tool_request


def _request(tool: str, arguments: dict):
    return build_tool_request_from_model_output(
        request_id=f"test-{tool}", tool=tool, arguments=arguments, actor="test", reason="unit test",
    )


class AssembleEvidenceBundleTests(unittest.TestCase):
    def test_refuses_an_empty_observed_list(self):
        with self.assertRaises(EvidenceAssemblyError):
            assemble_evidence_bundle([], impact="something is wrong")

    def test_refuses_an_empty_impact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HYDRA-UMC-EMPTY").mkdir()
            config = OrchestratorConfig(ecosystem_root=root)
            result = dispatch_tool_request(_request("manifest.read", {"project": "HYDRA-UMC-EMPTY"}), config)
            with self.assertRaises(EvidenceAssemblyError):
                assemble_evidence_bundle([ObservedResult("manifest.read", result)], impact="   ")

    def test_rejects_a_result_that_is_not_a_real_valid_tool_result(self):
        with self.assertRaises(ContractValidationError):
            assemble_evidence_bundle(
                [ObservedResult("manifest.read", {"not": "a real ToolResult"})],
                impact="a real observed problem",
            )

    def test_builds_a_real_valid_bundle_from_a_real_manifest_read(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "HYDRA-UMC-EXAMPLE"
            project_dir.mkdir()
            manifest = {"name": "HYDRA-UMC-EXAMPLE", "version": "1.2.3", "maturity": "functional", "role": "service"}
            (project_dir / "hydra-umc.project.json").write_text(json.dumps(manifest), encoding="utf-8")
            config = OrchestratorConfig(ecosystem_root=root)
            result = dispatch_tool_request(_request("manifest.read", {"project": "HYDRA-UMC-EXAMPLE"}), config)

            bundle = assemble_evidence_bundle(
                [ObservedResult("manifest.read", result)],
                impact="the manifest reports an unexpected version",
            )

            validate("EvidenceBundle", bundle)  # never raises
            self.assertEqual(bundle["componentVersions"], {"HYDRA-UMC-EXAMPLE": "1.2.3"})
            self.assertEqual(len(bundle["relevantManifests"]), 1)
            self.assertEqual(bundle["reproductionSteps"], [result["evidence"]])
            self.assertEqual(bundle["localValidationResult"], "no local validation was run - this evidence is limited to already-produced OBSERVE-level tool output")

    def test_collects_redacted_log_excerpts_from_a_real_logs_read(self):
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "server.log"
            log_path.write_text("line one\nline two\n", encoding="utf-8")
            config = OrchestratorConfig(log_sources={"server_log": log_path})
            result = dispatch_tool_request(_request("logs.read", {"name": "server_log"}), config)

            bundle = assemble_evidence_bundle(
                [ObservedResult("logs.read", result)],
                impact="the log shows an unexpected pattern",
            )

            self.assertEqual(bundle["redactedLogExcerpts"], ["line one", "line two"])

    def test_checksum_changes_when_the_real_content_changes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HYDRA-UMC-EMPTY").mkdir()
            config = OrchestratorConfig(ecosystem_root=root)
            result = dispatch_tool_request(_request("manifest.read", {"project": "HYDRA-UMC-EMPTY"}), config)

            bundle_a = assemble_evidence_bundle([ObservedResult("manifest.read", result)], impact="impact A")
            bundle_b = assemble_evidence_bundle([ObservedResult("manifest.read", result)], impact="impact B")

            self.assertNotEqual(bundle_a["checksum"], bundle_b["checksum"])

    def test_honors_caller_supplied_actions_attempted_and_failed_tests(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HYDRA-UMC-EMPTY").mkdir()
            config = OrchestratorConfig(ecosystem_root=root)
            result = dispatch_tool_request(_request("manifest.read", {"project": "HYDRA-UMC-EMPTY"}), config)

            bundle = assemble_evidence_bundle(
                [ObservedResult("manifest.read", result)],
                impact="a real observed problem",
                actions_attempted=["restarted the process manually"],
                failed_tests=["tests/unit/test_dispatch.py::SomeTest"],
                local_validation_result="ran the unit suite locally, one test failed",
            )

            self.assertEqual(bundle["actionsAttempted"], ["restarted the process manually"])
            self.assertEqual(bundle["failedTests"], ["tests/unit/test_dispatch.py::SomeTest"])
            self.assertEqual(bundle["localValidationResult"], "ran the unit suite locally, one test failed")


if __name__ == "__main__":
    unittest.main()
