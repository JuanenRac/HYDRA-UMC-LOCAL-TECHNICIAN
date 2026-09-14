# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_proposal.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 4's MaintenanceProposal half - grounding against real ToolResults,
same real-not-mocked convention as test_dispatch.py/test_evidence.py."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.contracts import validate
from hydra_umc_local_technician.escalation.evidence import ObservedResult
from hydra_umc_local_technician.escalation.proposal import ProposalError, UngroundedEvidenceError, propose_maintenance
from hydra_umc_local_technician.knowledge.trust import build_tool_request_from_model_output
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.orchestrator.dispatch import dispatch_tool_request
from hydra_umc_local_technician.policy.risk_levels import RiskLevel


def _request(tool: str, arguments: dict):
    return build_tool_request_from_model_output(
        request_id=f"test-{tool}", tool=tool, arguments=arguments, actor="test", reason="unit test",
    )


def _real_manifest_result(root: Path, project: str = "HYDRA-UMC-EMPTY") -> dict:
    (root / project).mkdir(exist_ok=True)
    config = OrchestratorConfig(ecosystem_root=root)
    return dispatch_tool_request(_request("manifest.read", {"project": project}), config)


class ProposeMaintenanceTests(unittest.TestCase):
    def test_builds_a_real_valid_proposal_grounded_in_real_evidence(self):
        with TemporaryDirectory() as tmp:
            result = _real_manifest_result(Path(tmp))
            pool = [ObservedResult("manifest.read", result)]

            proposal = propose_maintenance(
                diagnosis="the manifest was not found where expected",
                cited_evidence=[result["evidence"]],
                evidence_pool=pool,
                scope="HYDRA-UMC-EMPTY's own manifest file",
                risk=RiskLevel.REVERSIBLE_OPERATION,
                steps=["restore the manifest file from its last known-good commit"],
                rollback="delete the restored file if it turns out to be wrong",
            )

            validate("MaintenanceProposal", proposal)  # never raises
            self.assertEqual(proposal["risk"], "reversible_operation")
            self.assertTrue(proposal["confirmationRequired"])

    def test_refuses_evidence_not_backed_by_any_real_observed_result(self):
        with TemporaryDirectory() as tmp:
            result = _real_manifest_result(Path(tmp))
            pool = [ObservedResult("manifest.read", result)]

            with self.assertRaises(UngroundedEvidenceError):
                propose_maintenance(
                    diagnosis="something the technician made up",
                    cited_evidence=["this was never actually observed by any tool"],
                    evidence_pool=pool,
                    scope="anything",
                    risk=RiskLevel.PREPARE,
                    steps=["do something"],
                    rollback="undo it",
                )

    def test_refuses_an_empty_diagnosis(self):
        with self.assertRaises(ProposalError):
            propose_maintenance(
                diagnosis="", cited_evidence=["x"], evidence_pool=[], scope="x",
                risk=RiskLevel.PREPARE, steps=["x"], rollback="x",
            )

    def test_refuses_zero_cited_evidence(self):
        with self.assertRaises(ProposalError):
            propose_maintenance(
                diagnosis="a real problem", cited_evidence=[], evidence_pool=[], scope="x",
                risk=RiskLevel.PREPARE, steps=["x"], rollback="x",
            )

    def test_refuses_zero_steps(self):
        with TemporaryDirectory() as tmp:
            result = _real_manifest_result(Path(tmp))
            with self.assertRaises(ProposalError):
                propose_maintenance(
                    diagnosis="a real problem", cited_evidence=[result["evidence"]],
                    evidence_pool=[ObservedResult("manifest.read", result)], scope="x",
                    risk=RiskLevel.PREPARE, steps=[], rollback="x",
                )

    def test_refuses_a_non_risk_level_risk_argument(self):
        with self.assertRaises(ProposalError):
            propose_maintenance(
                diagnosis="a real problem", cited_evidence=["x"], evidence_pool=[], scope="x",
                risk="reversible_operation", steps=["x"], rollback="x",
            )

    def test_confirmation_required_always_matches_the_real_policy_for_the_given_risk(self):
        with TemporaryDirectory() as tmp:
            result = _real_manifest_result(Path(tmp))
            pool = [ObservedResult("manifest.read", result)]
            for risk in RiskLevel:
                proposal = propose_maintenance(
                    diagnosis="a real problem", cited_evidence=[result["evidence"]], evidence_pool=pool,
                    scope="x", risk=risk, steps=["x"], rollback="x",
                )
                from hydra_umc_local_technician.policy.risk_levels import POLICIES
                self.assertEqual(proposal["confirmationRequired"], POLICIES[risk].requires_confirmation)

    def test_defaults_pre_checks_expected_changes_and_explicit_limits_to_empty_lists(self):
        with TemporaryDirectory() as tmp:
            result = _real_manifest_result(Path(tmp))
            proposal = propose_maintenance(
                diagnosis="a real problem", cited_evidence=[result["evidence"]],
                evidence_pool=[ObservedResult("manifest.read", result)], scope="x",
                risk=RiskLevel.PREPARE, steps=["x"], rollback="x",
            )
            self.assertEqual(proposal["preChecks"], [])
            self.assertEqual(proposal["expectedChanges"], [])
            self.assertEqual(proposal["explicitLimits"], [])


if __name__ == "__main__":
    unittest.main()
