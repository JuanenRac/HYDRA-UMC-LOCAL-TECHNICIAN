# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_cli_tools_and_escalation.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 5's own first real slice: `tools list`/`tools call` and
`escalation evidence`/`escalation propose` - real, end-to-end CLI
invocations against a real temp directory, same real-not-mocked
convention every other test module here already uses."""
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.cli import main
from hydra_umc_local_technician.policy.tool_matrix import TOOL_MATRIX


def _run(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = main(argv)
    return exit_code, buffer.getvalue()


class ToolsListTests(unittest.TestCase):
    def test_lists_every_real_registered_tool(self):
        exit_code, output = _run(["tools", "list"])
        self.assertEqual(exit_code, 0)
        lines = [line for line in output.splitlines() if line.strip()]
        self.assertEqual(len(lines), len(TOOL_MATRIX))
        for name in TOOL_MATRIX:
            self.assertTrue(any(line.startswith(name + "\t") for line in lines), name)


class ToolsCallTests(unittest.TestCase):
    def test_calls_a_real_observe_tool_and_prints_a_real_tool_result(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps({"storagePaths": {"scratch": tmp}}), encoding="utf-8")

            exit_code, output = _run(["tools", "call", "storage.usage", "--arg", "name=scratch", "--config", str(config_path)])

            self.assertEqual(exit_code, 0)
            result = json.loads(output)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["output"]["name"], "scratch")

    def test_refuses_an_unregistered_tool(self):
        exit_code, output = _run(["tools", "call", "shell.exec"])
        self.assertEqual(exit_code, 1)

    def test_refuses_a_name_not_on_the_default_allow_list(self):
        exit_code, output = _run(["tools", "call", "storage.usage", "--arg", "name=not-configured"])
        self.assertEqual(exit_code, 1)

    def test_refuses_a_malformed_arg(self):
        exit_code, output = _run(["tools", "call", "storage.usage", "--arg", "not-a-key-value-pair"])
        self.assertEqual(exit_code, 1)


class EscalationEvidenceCommandTests(unittest.TestCase):
    def test_assembles_a_real_bundle_from_a_real_tools_call_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "HYDRA-UMC-EXAMPLE"
            project_dir.mkdir()
            manifest = {"name": "HYDRA-UMC-EXAMPLE", "version": "1.2.3", "maturity": "functional", "role": "service"}
            (project_dir / "hydra-umc.project.json").write_text(json.dumps(manifest), encoding="utf-8")
            config_path = root / "config.json"
            config_path.write_text(json.dumps({"ecosystemRoot": str(root)}), encoding="utf-8")

            call_exit, call_output = _run([
                "tools", "call", "manifest.read", "--arg", "project=HYDRA-UMC-EXAMPLE", "--config", str(config_path),
            ])
            self.assertEqual(call_exit, 0)
            result_path = root / "manifest_result.json"
            result_path.write_text(call_output, encoding="utf-8")

            evidence_exit, evidence_output = _run([
                "escalation", "evidence",
                "--result", f"manifest.read={result_path}",
                "--impact", "the manifest reports an unexpected version",
            ])

            self.assertEqual(evidence_exit, 0)
            bundle = json.loads(evidence_output)
            self.assertEqual(bundle["componentVersions"], {"HYDRA-UMC-EXAMPLE": "1.2.3"})

    def test_refuses_a_missing_impact(self):
        with TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "does-not-matter.json"
            result_path.write_text("{}", encoding="utf-8")
            exit_code, _ = _run(["escalation", "evidence", "--result", f"x={result_path}", "--impact", ""])
            self.assertEqual(exit_code, 1)

    def test_refuses_a_malformed_result_spec(self):
        exit_code, _ = _run(["escalation", "evidence", "--result", "not-a-key-value-pair", "--impact", "x"])
        self.assertEqual(exit_code, 1)


class EscalationProposeCommandTests(unittest.TestCase):
    def test_builds_a_real_proposal_grounded_in_a_real_tools_call_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HYDRA-UMC-EMPTY").mkdir()
            config_path = root / "config.json"
            config_path.write_text(json.dumps({"ecosystemRoot": str(root)}), encoding="utf-8")

            call_exit, call_output = _run([
                "tools", "call", "manifest.read", "--arg", "project=HYDRA-UMC-EMPTY", "--config", str(config_path),
            ])
            self.assertEqual(call_exit, 0)
            result_path = root / "result.json"
            result_path.write_text(call_output, encoding="utf-8")
            evidence_line = json.loads(call_output)["evidence"]

            propose_exit, propose_output = _run([
                "escalation", "propose",
                "--diagnosis", "the manifest was not found where expected",
                "--cited-evidence", evidence_line,
                "--result", f"manifest.read={result_path}",
                "--scope", "HYDRA-UMC-EMPTY's own manifest file",
                "--risk", "reversible_operation",
                "--step", "restore the manifest file from its last known-good commit",
                "--rollback", "delete the restored file if it turns out to be wrong",
            ])

            self.assertEqual(propose_exit, 0)
            proposal = json.loads(propose_output)
            self.assertEqual(proposal["risk"], "reversible_operation")
            self.assertTrue(proposal["confirmationRequired"])

    def test_refuses_ungrounded_evidence(self):
        with TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "result.json"
            result_path.write_text(json.dumps({
                "requestId": "x", "status": "ok", "output": {}, "evidence": "a real evidence string",
                "timestamp": "2026-01-01T00:00:00Z", "durationMs": 1.0, "toolVersion": "0.0.0", "errorCode": None,
            }), encoding="utf-8")

            exit_code, _ = _run([
                "escalation", "propose",
                "--diagnosis", "a made-up problem",
                "--cited-evidence", "this was never actually observed",
                "--result", f"manifest.read={result_path}",
                "--scope", "x", "--risk", "prepare", "--step", "x", "--rollback", "x",
            ])

            self.assertEqual(exit_code, 1)

    def test_refuses_an_unknown_risk_level(self):
        # argparse's own --choices rejection calls sys.exit() directly (a
        # real SystemExit, not a returned code) - the same real path
        # VersionTests.test_version_flag_exits_zero already exercises for
        # --version.
        with self.assertRaises(SystemExit) as ctx:
            _run([
                "escalation", "propose", "--diagnosis", "x", "--cited-evidence", "x", "--result", "x=x",
                "--scope", "x", "--risk", "not-a-real-level", "--step", "x", "--rollback", "x",
            ])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
