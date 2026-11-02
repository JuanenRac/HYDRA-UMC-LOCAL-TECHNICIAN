# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_runbooks_and_approvals.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Markdown runbook engine and the Ed25519 signed approvals, with the CLI commands that expose them."""
import copy
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.cli import main
from hydra_umc_local_technician.policy import approvals
from hydra_umc_local_technician.policy.execution_mode import ExecutionMode, decide
from hydra_umc_local_technician.policy.risk_levels import RiskLevel
from hydra_umc_local_technician.rules import runbook

REPO = Path(__file__).resolve().parents[2]
RESULT = {
    "requestId": "r1", "status": "ok", "output": {"unit": "x.service", "active": False, "available": True},
    "evidence": "systemctl is-active x.service: inactive", "timestamp": "2026-01-01T00:00:00Z", "durationMs": 1.0,
    "toolVersion": "0.1.9", "errorCode": None, "tool": "service.status",
}
MINIMAL = """---
id: t
risk: observe
scope: the thing
title: T
when: service.status output.value >= 5
---
## Diagnosis
d
## Steps
1. one
2. two
## Rollback
r
"""


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class RunbookTests(unittest.TestCase):
    def test_the_shipped_example_matches_and_builds_a_grounded_proposal_in_every_language(self):
        found = runbook.load_runbooks(REPO / "configs" / "runbooks")
        results = {"service.status": RESULT}
        matches = runbook.evaluate(found, results)
        self.assertEqual([m.runbook.runbook_id for m in matches], ["service-inactive"])
        for language in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            proposal = runbook.build_proposal(matches[0], results, language)
            self.assertEqual(proposal["citedEvidence"], [RESULT["evidence"]])
        self.assertIn("systemd", runbook.build_proposal(matches[0], results, "pt")["diagnosis"])
        self.assertTrue(runbook.build_proposal(matches[0], results, "ja")["diagnosis"].startswith("ユニット"))
        self.assertTrue(runbook.build_proposal(matches[0], results, "fr")["steps"][0].startswith("Read"))  # no French steps: default text

    def test_a_missing_failed_or_different_result_never_matches(self):
        found = runbook.load_runbooks(REPO / "configs" / "runbooks")
        active = copy.deepcopy(RESULT)
        active["output"]["active"] = True
        failed = copy.deepcopy(RESULT)
        failed["status"] = "error"
        for results in ({}, {"service.status": active}, {"service.status": failed}):
            self.assertEqual(runbook.evaluate(found, results), [])

    def test_operators_and_paths(self):
        results = {"t": {"status": "ok", "output": {"a": [{"n": 7}], "s": "hello", "b": True}}}

        def holds(line):
            return runbook._holds(runbook._parse_condition(line, "x"), results)
        self.assertTrue(holds("t a.0.n >= 7"))
        self.assertFalse(holds("t a.0.n > 7"))
        self.assertTrue(holds("t s contains ell"))
        self.assertTrue(holds("t b == true"))
        self.assertFalse(holds("t b == 1"))
        self.assertTrue(holds("t a.5 missing"))
        self.assertTrue(holds("t s exists"))
        self.assertFalse(holds("t s > 3"))
        self.assertFalse(holds("t nothing == 1"))

    def test_malformed_runbooks_are_refused(self):
        bad = [
            "no front matter", MINIMAL.replace("when: service.status output.value >= 5\n", ""), MINIMAL.replace("risk: observe", "risk: nope"),
            MINIMAL.replace("id: t", "id: Bad Id"), MINIMAL.replace(">= 5", ">= five"), MINIMAL.replace("when:", "bogus:"),
            MINIMAL.replace("## Rollback\nr\n", ""), MINIMAL + "## Mystery\nx\n", MINIMAL.replace("title: T", "title.xx: T"),
            MINIMAL.replace(">= 5", "frobnicate 5"),
        ]
        for text in bad:
            with self.assertRaises(runbook.RunbookError, msg=text):
                runbook.parse_runbook(text)
        self.assertEqual(runbook.parse_runbook(MINIMAL).sections["steps"][""], ["one", "two"])

    def test_the_engine_has_no_way_to_run_a_step(self):
        public = [name for name in dir(runbook) if not name.startswith("_")]
        self.assertFalse([name for name in public if "exec" in name.lower() or "apply" in name.lower() or "subprocess" in name.lower()])

    def test_the_cli_is_closed_until_the_config_opens_it(self):
        with TemporaryDirectory() as tmp:
            result = Path(tmp) / "r.json"
            result.write_text(json.dumps(RESULT), encoding="utf-8")
            config = Path(tmp) / "c.json"
            config.write_text(json.dumps({"runbooks": {"enabled": False, "directory": str(REPO / "configs" / "runbooks")}}), encoding="utf-8")
            code, _, err = _run(["runbook", "run", "--config", str(config), "--result", f"service.status={result}"])
            self.assertEqual((code, "closed" in err), (2, True))
            config.write_text(json.dumps({"runbooks": {"enabled": True, "directory": str(REPO / "configs" / "runbooks"), "language": "es"}}), encoding="utf-8")
            code, out, _ = _run(["runbook", "run", "--config", str(config), "--result", f"service.status={result}"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["matched"], ["service-inactive"])
            self.assertEqual(_run(["runbook", "check", str(REPO / "configs" / "runbooks")])[0], 0)


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        try:
            import cryptography  # noqa: F401
        except ImportError:
            self.skipTest("the 'cryptography' package is not installed")
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.private, self.public = self.dir / "ana.key", self.dir / "ana.pub.json"
        approvals.generate_keypair(self.private, self.public, "ana")
        self.store = approvals.TrustStore.load(self.dir / "trust.json")
        alias, key = approvals.read_public_key_file(self.public)
        self.store.add(alias, key)
        self.proposal = {"risk": "reversible_operation", "steps": ["restart"]}

    def sign(self, **kwargs):
        return approvals.sign_approval(self.private, "ana", "service.restart", self.proposal, ttl_seconds=kwargs.pop("ttl", 300), **kwargs)

    def verify(self, approval, **kwargs):
        return approvals.verify_approval(approval, kwargs.pop("proposal", self.proposal), kwargs.pop("action", "service.restart"), self.store,
                                         max_validity_seconds=900, **kwargs)

    def test_a_valid_approval_becomes_the_record_the_policy_asks_for(self):
        record = self.verify(self.sign())
        self.assertTrue(record.signature_verified)
        self.assertTrue(decide(ExecutionMode.ASSISTED, RiskLevel.REVERSIBLE_OPERATION, "service.restart", record).allowed)
        self.assertFalse(decide(ExecutionMode.DIAGNOSIS_ONLY, RiskLevel.REVERSIBLE_OPERATION, "service.restart", record).allowed)

    def test_every_tampering_is_refused(self):
        approval = self.sign(now=1_000.0)
        cases = [
            (dict(approval, action="service.stop"), {}), (dict(approval, signature=approval["signature"][:-4] + "AAAA"), {}),
            (dict(approval, approver="bob"), {}), (dict(approval, expiresAt=approval["expiresAt"] + 1), {}),
            (approval, {"proposal": {"risk": "reversible_operation", "steps": ["format"]}}), (approval, {"action": "service.stop"}),
            (approval, {"now": 1_000.0 + 301}), (approval, {"now": 1_000.0 - 3600}), (self.sign(ttl=5000, now=1_000.0), {"now": 1_001.0}),
            ({"junk": 1}, {}),
        ]
        for approval_doc, extra in cases:
            extra.setdefault("now", 1_001.0)
            with self.assertRaises(approvals.ApprovalError, msg=(approval_doc, extra)):
                self.verify(approval_doc, **extra)

    def test_a_signature_from_a_key_that_is_not_trusted_is_refused(self):
        other_private, other_public = self.dir / "eve.key", self.dir / "eve.pub.json"
        approvals.generate_keypair(other_private, other_public, "ana")
        forged = approvals.sign_approval(other_private, "ana", "service.restart", self.proposal, ttl_seconds=60)
        with self.assertRaises(approvals.ApprovalError):
            self.verify(forged)

    def test_an_approval_can_be_used_once_when_the_nonce_file_is_set(self):
        nonces = self.dir / "nonces.json"
        approval = self.sign()
        self.verify(approval, used_nonces=nonces)
        with self.assertRaises(approvals.ApprovalError):
            self.verify(approval, used_nonces=nonces)

    def test_keys_are_not_overwritten_and_never_made_inside_a_git_tree(self):
        with self.assertRaises(approvals.ApprovalError):
            approvals.generate_keypair(self.private, self.dir / "other.pub", "ana")
        with self.assertRaises(approvals.ApprovalError):
            approvals.generate_keypair(REPO / "tests" / "x.key", self.dir / "x.pub", "ana")
        self.assertFalse((REPO / "tests" / "x.key").exists())

    def test_an_alias_cannot_be_silently_pointed_at_another_key(self):
        other_private, other_public = self.dir / "o.key", self.dir / "o.pub.json"
        approvals.generate_keypair(other_private, other_public, "ana")
        _, key = approvals.read_public_key_file(other_public)
        with self.assertRaises(approvals.ApprovalError):
            self.store.add("ana", key)
        self.store.add("ana", key, replace=True)
        self.store.export("ana", self.dir / "exported.json")
        self.assertEqual(approvals.read_public_key_file(self.dir / "exported.json"), ("ana", key))
        self.assertEqual(approvals.TrustStore.load(self.dir / "trust.json").keys["ana"], key)

    def test_the_cli_round_trip(self):
        config = self.dir / "c.json"
        config.write_text(json.dumps({"approvals": {"enabled": True, "trustStore": str(self.dir / "t2.json"), "maxValiditySeconds": 600}}), encoding="utf-8")
        proposal = self.dir / "p.json"
        proposal.write_text(json.dumps(self.proposal), encoding="utf-8")
        self.assertEqual(_run(["approval", "trust", "add", "--config", str(config), "--public-key-file", str(self.public)])[0], 0)
        self.assertIn("ana", _run(["approval", "trust", "list", "--config", str(config)])[1])
        signed = self.dir / "a.json"
        self.assertEqual(_run(["approval", "sign", "--private", str(self.private), "--approver", "ana", "--action", "service.restart",
                               "--proposal", str(proposal), "--output", str(signed)])[0], 0)
        base = ["approval", "verify", "--config", str(config), "--approval", str(signed), "--proposal", str(proposal)]
        code, out, _ = _run(base + ["--action", "service.restart"])
        self.assertEqual((code, "APPROVED: ana" in out), (0, True))
        self.assertEqual(_run(base + ["--action", "service.stop"])[0], 2)

    def test_the_approval_commands_are_closed_by_default(self):
        config = self.dir / "closed.json"
        config.write_text("{}", encoding="utf-8")
        code, _, err = _run(["approval", "trust", "list", "--config", str(config)])
        self.assertEqual((code, "closed" in err), (2, True))


if __name__ == "__main__":
    unittest.main()
