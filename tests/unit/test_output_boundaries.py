# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_output_boundaries.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Nothing that leaves the technician carries a secret, a proposal is grounded
only in real tool results, and configuration / argument edge cases are refused
with one line instead of being silently reinterpreted."""
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.cli import main
from hydra_umc_local_technician.escalation.evidence import ObservedResult, assemble_evidence_bundle
from hydra_umc_local_technician.escalation.proposal import ProposalError, propose_maintenance
from hydra_umc_local_technician.knowledge import index as knowledge_index
from hydra_umc_local_technician.knowledge.redaction import redact_json, redact_secrets
from hydra_umc_local_technician.knowledge.trust import (
    ToolCallRefused,
    UntrustedText,
    build_tool_request_from_model_output,
)
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.orchestrator.dispatch import dispatch_tool_request
from hydra_umc_local_technician.policy.risk_levels import RiskLevel


def _request(tool: str, arguments: dict):
    return build_tool_request_from_model_output(
        request_id=f"test-{tool}", tool=tool, arguments=arguments, actor="test", reason="unit test",
    )


class RedactionCostTest(unittest.TestCase):
    def test_a_huge_run_without_a_secret_is_redacted_in_linear_time(self) -> None:
        import time
        for payload in ("x" * 1_000_000, "a-" * 300_000, "http" + "p" * 300_000, "xxxx://" * 20_000):
            started = time.monotonic()
            self.assertEqual(redact_secrets(payload), payload)
            self.assertLess(time.monotonic() - started, 10.0, payload[:6])

    def test_the_bounded_url_patterns_still_redact_normal_credentials(self) -> None:
        cleaned = redact_secrets("see https://admin:hunter2@host/x and https://abcdef0123456789abcdef@git/y")
        self.assertNotIn("hunter2", cleaned)
        self.assertNotIn("abcdef0123456789abcdef", cleaned)


class RedactionShapesTest(unittest.TestCase):
    def test_a_secret_given_as_a_separate_command_line_argument_is_redacted(self) -> None:
        line = redact_secrets("streamer --token hunter2-token-value --password=swordfish --port 8080 -api-key abc123456")
        for secret in ("hunter2-token-value", "swordfish", "abc123456"):
            self.assertNotIn(secret, line)
        self.assertIn("--port 8080", line)

    def test_other_common_credential_shapes_are_redacted(self) -> None:
        samples = {
            "basic": "Authorization: Basic dXNlcjpwYXNzd29yZA==",
            "cookie": "Cookie: session=abcdef0123456789; theme=dark",
            "github": "clone https://ghp_abcdefghijklmnopqrstuvwxyz0123456789@github.com/x/y",
            "aws": "key AKIAABCDEFGHIJKLMNOP in the log",
            "anthropic": "using sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
        }
        for name, text in samples.items():
            cleaned = redact_secrets(text)
            self.assertIn("[REDACTED]", cleaned, name)
        self.assertNotIn("dXNlcjpwYXNzd29yZA", redact_secrets(samples["basic"]))
        self.assertNotIn("abcdef0123456789", redact_secrets(samples["cookie"]))
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz", redact_secrets(samples["github"]))
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", redact_secrets(samples["aws"]))

    def test_redact_json_cleans_nested_values_and_secret_named_keys(self) -> None:
        cleaned = redact_json({"url": "http://admin:hunter2@host/", "list": ["--token abc12345"], "password": "x", "n": 3})
        text = json.dumps(cleaned)
        self.assertNotIn("hunter2", text)
        self.assertNotIn("abc12345", text)
        self.assertEqual(cleaned["password"], "[REDACTED]")
        self.assertEqual(cleaned["n"], 3)


class ToolResultAndBundleAreCleanTest(unittest.TestCase):
    def test_a_credential_in_a_configured_target_never_reaches_the_tool_result(self) -> None:
        config = OrchestratorConfig(
            storage_paths={}, ports={}, connectivity_targets={"x": "http://admin:hunter2@127.0.0.1:9/"},
            systemd_units=(), ecosystem_root=None, log_sources={}, process_patterns={}, knowledge_sources={},
        )
        result = dispatch_tool_request(_request("network.connectivity", {"name": "x"}), config)
        self.assertNotIn("hunter2", json.dumps(result))

    def test_every_free_text_field_of_the_bundle_is_redacted(self) -> None:
        result = {
            "requestId": "r1", "status": "ok", "output": {}, "evidence": "ran with --token hunter2-secret",
            "timestamp": "2026-01-01T00:00:00Z", "durationMs": 1.0, "toolVersion": "0", "errorCode": None,
        }
        bundle = assemble_evidence_bundle(
            [ObservedResult("logs.read", result)], impact="password=swordfish broke it",
            local_validation_result="token: abc123456789", actions_attempted=["--api-key key123456"],
            failed_tests=["Authorization: Bearer abcdef123456"],
        )
        text = json.dumps(bundle)
        for secret in ("hunter2-secret", "swordfish", "abc123456789", "key123456", "abcdef123456"):
            self.assertNotIn(secret, text)


class ProposalGroundingTest(unittest.TestCase):
    def _propose(self, result: dict):
        return propose_maintenance(
            diagnosis="d", cited_evidence=["forged"], evidence_pool=[ObservedResult("logs.read", result)],
            scope="s", risk=RiskLevel.INFORM, steps=["look"], rollback="none",
        )

    def test_an_object_that_is_not_a_valid_tool_result_cannot_ground_a_proposal(self) -> None:
        with self.assertRaises(ProposalError):
            self._propose({"evidence": "forged"})

    def test_a_failed_tool_call_grounds_nothing(self) -> None:
        failed = {
            "requestId": "r1", "status": "error", "output": {}, "evidence": "forged",
            "timestamp": "2026-01-01T00:00:00Z", "durationMs": 1.0, "toolVersion": "0", "errorCode": "X",
        }
        with self.assertRaises(ProposalError):
            self._propose(failed)

    def test_the_cli_reports_a_malformed_result_in_one_line(self) -> None:
        with TemporaryDirectory() as tmp:
            bad = Path(tmp) / "r.json"
            bad.write_text(json.dumps({"foo": 1}), encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                code = main([
                    "escalation", "propose", "--diagnosis", "d", "--cited-evidence", "x", "--result", f"logs.read={bad}",
                    "--scope", "s", "--risk", "inform", "--step", "look", "--rollback", "none",
                ])
            self.assertEqual(code, 2)
            self.assertTrue(err.getvalue().startswith("REFUSED:"))


class InputEdgesTest(unittest.TestCase):
    def test_untrusted_text_cannot_become_part_of_a_tool_request(self) -> None:
        with self.assertRaises(ToolCallRefused):
            build_tool_request_from_model_output(
                request_id="r", tool="logs.read", arguments={"name": UntrustedText("server")}, actor="a", reason="r",
            )
        with self.assertRaises(ToolCallRefused):
            build_tool_request_from_model_output(
                request_id="r", tool="logs.read", arguments={}, actor="a", reason=UntrustedText("because"),
            )

    def test_a_config_with_a_bare_string_unit_list_is_refused(self) -> None:
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "c.json"
            config.write_text(json.dumps({"systemdUnits": "hydra-umc-server"}), encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                try:
                    code = main(["tools", "call", "service.status", "--config", str(config), "--arg", "unit=hydra-umc-server"])
                except ValueError:
                    code = "raised"
            # either a one-line refusal, or the validator's ValueError surfacing - never a tuple of letters
            self.assertNotEqual(code, 0)

    def test_a_boolean_is_not_a_line_count(self) -> None:
        with TemporaryDirectory() as tmp:
            log = Path(tmp) / "server.log"
            log.write_text("\n".join(f"line {i}" for i in range(50)), encoding="utf-8")
            config = OrchestratorConfig(
                storage_paths={}, ports={}, connectivity_targets={}, systemd_units=(), ecosystem_root=None,
                log_sources={"server": log}, process_patterns={}, knowledge_sources={},
            )
            result = dispatch_tool_request(_request("logs.read", {"name": "server", "lines": True}), config)
            self.assertGreater(len(result["output"]["lines"]), 1)

    def test_a_urtc_project_reads_its_own_manifest_file(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "URTC-CORE").mkdir()
            (root / "URTC-CORE" / "urtc.project.json").write_text(
                json.dumps({"name": "URTC-CORE", "version": "1.2.3", "maturity": "functional", "role": "service"}),
                encoding="utf-8",
            )
            config = OrchestratorConfig(
                storage_paths={}, ports={}, connectivity_targets={}, systemd_units=(), ecosystem_root=root,
                log_sources={}, process_patterns={}, knowledge_sources={},
            )
            result = dispatch_tool_request(_request("manifest.read", {"project": "URTC-CORE"}), config)
            self.assertTrue(result["output"]["found"])
            self.assertEqual(result["output"]["version"], "1.2.3")


class BoundedIndexWalkTest(unittest.TestCase):
    def test_excluded_directories_and_lock_files_are_not_indexed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "guide.md").write_text("# Guide\nmotor cooling notes", encoding="utf-8")
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "readme.md").write_text("# Pkg\nvendor noise", encoding="utf-8")
            (root / "package-lock.json").write_text('{"lockfileVersion": 3}', encoding="utf-8")
            result = knowledge_index.ingest_source_directory(root)
            self.assertEqual(list(result.indexed_sources), ["docs/guide.md"])

    def test_the_total_size_is_bounded(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for number in range(6):
                (root / f"doc{number}.md").write_text(f"# Doc {number}\ntext", encoding="utf-8")
            original = knowledge_index.MAX_TOTAL_BYTES
            knowledge_index.MAX_TOTAL_BYTES = 40
            try:
                result = knowledge_index.ingest_source_directory(root)
            finally:
                knowledge_index.MAX_TOTAL_BYTES = original
            self.assertTrue(result.truncated)
            self.assertLess(len(result.indexed_sources), 6)


if __name__ == "__main__":
    unittest.main()
