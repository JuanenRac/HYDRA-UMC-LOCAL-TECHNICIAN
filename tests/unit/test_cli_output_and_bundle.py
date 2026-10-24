# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_cli_output_and_bundle.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The ways of chaining the commands without carrying files by hand: --output, --from-bundle and the exit codes."""
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.cli import EXIT_ERROR, EXIT_REFUSED, main


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def _tool_result(root: Path) -> tuple[Path, str]:
    (root / "HYDRA-UMC-EMPTY").mkdir(exist_ok=True)
    config = root / "config.json"
    config.write_text(json.dumps({"ecosystemRoot": str(root)}), encoding="utf-8")
    result = root / "result.json"
    code, out, _ = _run(["tools", "call", "manifest.read", "--arg", "project=HYDRA-UMC-EMPTY", "--config", str(config), "--output", str(result)])
    assert code == 0, out
    return result, json.loads(result.read_text(encoding="utf-8"))["evidence"]


PROPOSAL_ARGS = ["--diagnosis", "the manifest was not found", "--scope", "the manifest", "--risk", "reversible_operation",
                 "--step", "restore it", "--rollback", "remove it again"]


class ExitCodeTests(unittest.TestCase):
    def test_the_codes_mean_error_and_refused(self):
        self.assertEqual((EXIT_ERROR, EXIT_REFUSED), (1, 2))

    def test_a_request_refused_before_it_runs_is_2_and_an_error_result_is_1(self):
        with TemporaryDirectory() as tmp:
            code, _, err = _run(["tools", "call", "no.such.tool"])
            self.assertEqual(code, 2)
            self.assertTrue(err.startswith("REFUSED:"))
            # a tool that runs and answers with an error: the unit does not exist on this machine's allow-list, so the call is refused too;
            # an allow-listed unit that fails is an error status. Use a storage name the config knows but whose path is missing.
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps({"storagePaths": {"gone": str(Path(tmp) / "does-not-exist")}}), encoding="utf-8")
            code, out, _ = _run(["tools", "call", "storage.usage", "--arg", "name=gone", "--config", str(config)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["status"], "error")


class OutputOptionTests(unittest.TestCase):
    def test_the_result_goes_to_the_file_not_to_the_screen(self):
        with TemporaryDirectory() as tmp:
            result, _ = _tool_result(Path(tmp))
            data = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "ok")
            code, out, _ = _run(["tools", "call", "manifest.read", "--arg", "project=HYDRA-UMC-EMPTY", "--config", str(Path(tmp) / "config.json"), "--output", str(result)])
            self.assertEqual(code, 0)
            self.assertIn("OK: manifest.read ->", out)
            self.assertNotIn('"requestId"', out)
            self.assertFalse(list(Path(tmp).glob("*.tmp")), "no half-written file is left behind")

    def test_an_output_that_cannot_be_written_is_refused(self):
        with TemporaryDirectory() as tmp:
            _tool_result(Path(tmp))
            code, _, err = _run(["tools", "call", "manifest.read", "--arg", "project=HYDRA-UMC-EMPTY", "--config", str(Path(tmp) / "config.json"),
                                 "--output", str(Path(tmp) / "no-such-folder" / "r.json")])
            self.assertEqual(code, 2)
            self.assertIn("cannot write --output", err)


class FromBundleTests(unittest.TestCase):
    def _bundle(self, root: Path) -> tuple[Path, str]:
        result, evidence = _tool_result(root)
        bundle = root / "bundle.json"
        code, out, err = _run(["escalation", "evidence", "--result", f"manifest.read={result}", "--impact", "the cell cannot start", "--output", str(bundle)])
        self.assertEqual(code, 0, err)
        self.assertIn("EVIDENCE_BUNDLE ->", out)
        return bundle, evidence

    def test_a_proposal_cites_the_evidence_of_a_bundle_without_the_result_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, evidence = self._bundle(root)
            proposal = root / "proposal.json"
            code, out, err = _run(["escalation", "propose", "--cited-evidence", evidence, "--from-bundle", str(bundle), "--output", str(proposal), *PROPOSAL_ARGS])
            self.assertEqual(code, 0, err)
            self.assertIn("MAINTENANCE_PROPOSAL ->", out)
            data = json.loads(proposal.read_text(encoding="utf-8"))
            self.assertEqual(data["citedEvidence"], [evidence])
            self.assertTrue(data["confirmationRequired"])

    def test_evidence_the_bundle_does_not_hold_is_not_citable(self):
        with TemporaryDirectory() as tmp:
            bundle, _ = self._bundle(Path(tmp))
            code, _, err = _run(["escalation", "propose", "--cited-evidence", "never observed", "--from-bundle", str(bundle), *PROPOSAL_ARGS])
            self.assertEqual(code, 2)
            self.assertIn("REFUSED", err)

    def test_a_bundle_edited_after_it_was_assembled_is_refused(self):
        with TemporaryDirectory() as tmp:
            bundle, evidence = self._bundle(Path(tmp))
            data = json.loads(bundle.read_text(encoding="utf-8"))
            data["reproductionSteps"].append("a step somebody added later")
            bundle.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run(["escalation", "propose", "--cited-evidence", "a step somebody added later", "--from-bundle", str(bundle), *PROPOSAL_ARGS])
            self.assertEqual(code, 2)
            self.assertIn("checksum", err)
            data["impact"] = "changed"
            bundle.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run(["escalation", "propose", "--cited-evidence", evidence, "--from-bundle", str(bundle), *PROPOSAL_ARGS])
            self.assertEqual(code, 2)

    def test_a_file_that_is_not_a_bundle_is_refused(self):
        with TemporaryDirectory() as tmp:
            junk = Path(tmp) / "junk.json"
            junk.write_text(json.dumps({"reproductionSteps": ["x"]}), encoding="utf-8")
            code, _, err = _run(["escalation", "propose", "--cited-evidence", "x", "--from-bundle", str(junk), *PROPOSAL_ARGS])
            self.assertEqual(code, 2)
            self.assertIn("not a valid EvidenceBundle", err)

    def test_without_results_or_a_bundle_nothing_is_proposed(self):
        code, _, err = _run(["escalation", "propose", "--cited-evidence", "x", *PROPOSAL_ARGS])
        self.assertEqual(code, 2)
        self.assertIn("--from-bundle", err)


if __name__ == "__main__":
    unittest.main()
