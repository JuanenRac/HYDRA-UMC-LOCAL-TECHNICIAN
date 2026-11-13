# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_cli_extra_flows.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Whole command flows of the extra commands, run through the real entry point: keys, trust store, signing, verifying and runbooks."""
import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.cli import main

try:
    import cryptography  # noqa: F401
    HAVE_CRYPTO = True
except ImportError:  # pragma: no cover
    HAVE_CRYPTO = False

REPO = Path(__file__).resolve().parents[2]
PROPOSAL = {"id": "p1", "risk": "reversible_operation", "steps": ["restart"]}


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


@unittest.skipUnless(HAVE_CRYPTO, "needs the cryptography package")
class ApprovalFlow(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.config = self.dir / "settings.json"
        self.config.write_text(json.dumps({"approvals": {
            "enabled": True, "trustStore": str(self.dir / "trust.json"), "maxValiditySeconds": 600,
            "usedNonces": str(self.dir / "nonces.json")}}), encoding="utf-8")
        self.proposal = self.dir / "proposal.json"
        self.proposal.write_text(json.dumps(PROPOSAL), encoding="utf-8")
        self.private, self.public = self.dir / "k" / "ana.key", self.dir / "k" / "ana.pub.json"
        code = run(["approval", "keygen", "--alias", "ana", "--private", str(self.private), "--public", str(self.public)])[0]
        self.assertEqual(code, 0)

    def trust(self, *extra):
        return run(["approval", "trust", extra[0], "--config", str(self.config), *extra[1:]])

    def sign(self, name="a.json", **kw):
        output = self.dir / name
        code, _out, err = run(["approval", "sign", "--private", str(self.private), "--approver", kw.get("approver", "ana"),
                               "--action", kw.get("action", "service.restart"), "--proposal", str(self.proposal),
                               "--valid-for", str(kw.get("valid_for", 300)), "--output", str(output)])
        return code, output, err

    def verify(self, approval, action="service.restart"):
        return run(["approval", "verify", "--config", str(self.config), "--approval", str(approval),
                    "--proposal", str(self.proposal), "--action", action])

    def test_the_full_round_trip_and_the_single_use_of_an_approval(self):
        code, out, _ = self.trust("add", "--public-key-file", str(self.public))
        self.assertEqual(code, 0)
        self.assertIn("TRUSTED: ana FINGERPRINT:", out)
        code, out, _ = self.trust("list")
        self.assertEqual((code, out.split("\t")[0]), (0, "ana"))
        code, approval, _ = self.sign()
        self.assertEqual(code, 0)
        code, out, err = self.verify(approval)
        self.assertEqual(code, 0, err)
        self.assertIn("APPROVED: ana for service.restart", out)
        code, _, err = self.verify(approval)
        self.assertNotEqual(code, 0)
        self.assertIn("already used", err)
        self.assertNotIn("Traceback", err)

    def test_an_approval_for_another_action_or_an_untrusted_signer_is_refused(self):
        self.trust("add", "--public-key-file", str(self.public))
        _, approval, _ = self.sign()
        code, _, err = self.verify(approval, action="service.stop")
        self.assertNotEqual(code, 0)
        self.assertIn("REFUSED", err)
        self.assertEqual(self.trust("remove", "--alias", "ana")[0], 0)
        code, _, err = self.verify(approval)
        self.assertNotEqual(code, 0)
        self.assertIn("nobody is trusted", err)

    def test_trust_export_replace_and_unknown_aliases(self):
        self.trust("add", "--public-key-file", str(self.public), "--alias", "boss")
        exported = self.dir / "out.pub.json"
        code, out, _ = self.trust("export", "--alias", "boss", "--output", str(exported))
        self.assertEqual(code, 0)
        self.assertIn("EXPORTED: boss", out)
        other_private, other_public = self.dir / "o" / "x.key", self.dir / "o" / "x.pub.json"
        run(["approval", "keygen", "--alias", "boss", "--private", str(other_private), "--public", str(other_public)])
        code, _, err = self.trust("add", "--public-key-file", str(other_public), "--alias", "boss")
        self.assertNotEqual(code, 0)
        self.assertIn("already trusts another key", err)
        self.assertEqual(self.trust("add", "--public-key-file", str(other_public), "--alias", "boss", "--replace")[0], 0)
        for command in (("remove", "--alias", "nobody"), ("export", "--alias", "nobody", "--output", str(self.dir / "z.json"))):
            code, _, err = self.trust(*command)
            self.assertNotEqual(code, 0)
            self.assertIn("no key is trusted", err)

    def test_signing_refuses_a_missing_proposal_and_an_empty_action(self):
        code, _, err = run(["approval", "sign", "--private", str(self.private), "--approver", "ana", "--action", "x",
                            "--proposal", str(self.dir / "absent.json"), "--output", str(self.dir / "o.json")])
        self.assertNotEqual(code, 0)
        self.assertNotIn("Traceback", err)
        code, _, _ = self.sign(action=" ")
        self.assertNotEqual(code, 0)
        code, _, _ = self.sign(valid_for=0)
        self.assertNotEqual(code, 0)
        self.assertFalse((self.dir / "o.json").exists())

    def test_keygen_never_overwrites(self):
        code, _, err = run(["approval", "keygen", "--alias", "ana", "--private", str(self.private), "--public", str(self.dir / "again.json")])
        self.assertNotEqual(code, 0)
        self.assertIn("already exists", err)


class RunbookFlow(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def settings(self, enabled=True, language="en"):
        path = self.dir / "settings.json"
        path.write_text(json.dumps({"runbooks": {"enabled": enabled, "directory": str(REPO / "configs" / "runbooks"), "language": language}}), encoding="utf-8")
        return str(path)

    def test_check_counts_the_shipped_runbooks_and_refuses_a_missing_directory(self):
        code, out, _ = run(["runbook", "check", str(REPO / "configs" / "runbooks")])
        self.assertEqual(code, 0)
        self.assertRegex(out, r"VALID: [1-9][0-9]* runbook")
        code, _, err = run(["runbook", "check", str(self.dir / "absent")])
        self.assertNotEqual(code, 0)
        self.assertNotIn("Traceback", err)

    def test_run_with_no_matching_result_proposes_nothing_and_writes_the_output_file(self):
        result = self.dir / "r.json"
        result.write_text(json.dumps({"tool": "service.status", "status": "ok", "output": {"unit": "x", "active": True, "available": True},
                                      "evidence": "systemctl is-active x: active"}), encoding="utf-8")
        target = self.dir / "proposals.json"
        code, out, err = run(["runbook", "run", "--config", self.settings(), "--result", f"service.status={result}", "--output", str(target)])
        self.assertEqual(code, 0, err)
        self.assertIn("RUNBOOKS: 0 proposal(s)", out)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"matched": [], "proposals": {}})

    def test_run_refuses_a_closed_switch_a_malformed_result_argument_and_a_missing_file(self):
        code, _, err = run(["runbook", "run", "--config", self.settings(enabled=False), "--result", "a.b=x"])
        self.assertNotEqual(code, 0)
        self.assertIn("closed", err)
        code, _, err = run(["runbook", "run", "--config", self.settings(), "--result", "no-equals-sign"])
        self.assertNotEqual(code, 0)
        self.assertIn("--result must be", err)
        missing = self.dir / "absent.json"
        code, _, err = run(["runbook", "run", "--config", self.settings(), "--result", f"a.b={missing}"])
        self.assertNotEqual(code, 0)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
