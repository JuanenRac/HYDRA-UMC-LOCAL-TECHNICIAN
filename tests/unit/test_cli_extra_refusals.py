# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_cli_extra_refusals.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The refusal paths of the extra commands: a closed switch, a bad argument, a missing or damaged file.

Each one must end with one line for the operator and a non-zero exit code, never a traceback, and must write nothing.
"""
import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.cli import main


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def config(root: Path, **sections) -> str:
    path = root / "settings.json"
    path.write_text(json.dumps(sections), encoding="utf-8")
    return str(path)


class QueueRefusals(unittest.TestCase):
    def test_a_missing_bundle_file_is_refused_and_the_outbox_stays_empty(self):
        with TemporaryDirectory() as tmp:
            outbox = Path(tmp) / "outbox"
            code, out, err = run(["escalation", "queue", "--bundle", str(Path(tmp) / "nope.json"), "--outbox", str(outbox)])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)
            self.assertFalse(list(outbox.glob("*"))) if outbox.exists() else None

    def test_a_bundle_that_is_not_json_is_refused(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            bundle.write_text("{not json", encoding="utf-8")
            code, out, err = run(["escalation", "queue", "--bundle", str(bundle), "--outbox", str(Path(tmp) / "o")])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)

    def test_a_bundle_with_a_wrong_checksum_is_refused(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            bundle.write_text(json.dumps({"checksum": "0" * 64, "items": []}), encoding="utf-8")
            code, out, err = run(["escalation", "queue", "--bundle", str(bundle), "--outbox", str(Path(tmp) / "o")])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)


class SendRefusals(unittest.TestCase):
    def test_send_with_the_transport_closed_is_refused(self):
        with TemporaryDirectory() as tmp:
            cfg = config(Path(tmp), transport={"enabled": False})
            code, out, err = run(["escalation", "send", "--outbox", str(Path(tmp) / "o"), "--config", cfg])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)

    def test_send_with_a_missing_configuration_is_refused(self):
        with TemporaryDirectory() as tmp:
            code, out, err = run(["escalation", "send", "--outbox", str(Path(tmp) / "o"), "--config", str(Path(tmp) / "none.json")])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)


class RunbookRefusals(unittest.TestCase):
    def test_check_of_an_empty_directory_is_valid_with_zero_runbooks(self):
        with TemporaryDirectory() as tmp:
            code, out, err = run(["runbook", "check", tmp])
            self.assertEqual(code, 0)
            self.assertIn("VALID: 0 runbook(s)", out)

    def test_check_of_a_missing_directory_is_refused_in_one_line(self):
        with TemporaryDirectory() as tmp:
            code, out, err = run(["runbook", "check", str(Path(tmp) / "absent")])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)

    def test_run_with_the_rules_closed_is_refused(self):
        with TemporaryDirectory() as tmp:
            cfg = config(Path(tmp), runbooks={"enabled": False})
            code, out, err = run(["runbook", "run", "--config", cfg, "--result", "a.b=x.json"])
            self.assertNotEqual(code, 0)
            self.assertIn("closed", out + err)

    def test_run_with_a_result_that_has_no_equals_sign_is_refused(self):
        with TemporaryDirectory() as tmp:
            rules = Path(tmp) / "rules"
            rules.mkdir()
            cfg = config(Path(tmp), runbooks={"enabled": True, "directory": str(rules.resolve()), "language": "en"})
            code, out, err = run(["runbook", "run", "--config", cfg, "--result", "just-a-path.json"])
            self.assertNotEqual(code, 0)
            self.assertIn("tool.name=path", out + err)

    def test_run_with_a_missing_result_file_is_refused(self):
        with TemporaryDirectory() as tmp:
            rules = Path(tmp) / "rules"
            rules.mkdir()
            cfg = config(Path(tmp), runbooks={"enabled": True, "directory": str(rules.resolve()), "language": "en"})
            code, out, err = run(["runbook", "run", "--config", cfg, "--result", f"a.b={Path(tmp) / 'none.json'}"])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)

    def test_run_with_no_runbook_matching_prints_an_empty_proposal_set(self):
        with TemporaryDirectory() as tmp:
            rules = Path(tmp) / "rules"
            rules.mkdir()
            result = Path(tmp) / "r.json"
            result.write_text("{}", encoding="utf-8")
            cfg = config(Path(tmp), runbooks={"enabled": True, "directory": str(rules.resolve()), "language": "en"})
            output = Path(tmp) / "out.json"
            code, out, err = run(["runbook", "run", "--config", cfg, "--result", f"a.b={result}", "--output", str(output)])
            self.assertEqual(code, 0)
            self.assertIn("RUNBOOKS: 0 proposal(s)", out)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"matched": [], "proposals": {}})


class ApprovalRefusals(unittest.TestCase):
    def test_trust_list_with_approvals_closed_is_refused(self):
        with TemporaryDirectory() as tmp:
            cfg = config(Path(tmp), approvals={"enabled": False})
            code, out, err = run(["approval", "trust", "list", "--config", cfg])
            self.assertNotEqual(code, 0)
            self.assertIn("closed", out + err)

    def test_verify_with_approvals_closed_is_refused(self):
        with TemporaryDirectory() as tmp:
            cfg = config(Path(tmp), approvals={"enabled": False})
            code, out, err = run(["approval", "verify", "--config", cfg, "--approval", "a.json", "--proposal", "p.json", "--action", "x"])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)

    def test_sign_with_a_missing_private_key_is_refused(self):
        with TemporaryDirectory() as tmp:
            proposal = Path(tmp) / "p.json"
            proposal.write_text("{}", encoding="utf-8")
            code, out, err = run(["approval", "sign", "--private", str(Path(tmp) / "none.key"), "--approver", "me", "--action", "x",
                                  "--proposal", str(proposal), "--output", str(Path(tmp) / "a.json")])
            self.assertNotEqual(code, 0)
            self.assertNotIn("Traceback", out + err)
            self.assertFalse((Path(tmp) / "a.json").exists())

    def test_keygen_makes_a_pair_and_refuses_to_overwrite_it(self):
        with TemporaryDirectory() as tmp:
            private, public = Path(tmp) / "k.key", Path(tmp) / "k.pub"
            args = ["approval", "keygen", "--alias", "me", "--private", str(private), "--public", str(public)]
            code, out, _ = run(args)
            self.assertEqual(code, 0)
            self.assertIn("FINGERPRINT:", out)
            before = private.read_bytes()
            code, out, err = run(args)
            self.assertNotEqual(code, 0)
            self.assertEqual(private.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
