# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_audit_log.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The append-only audit journal: what is written, the hash chain, rotation, redaction and fail-closed."""
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician import cli
from hydra_umc_local_technician.knowledge.trust import build_tool_request_from_model_output
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.orchestrator.audit import GENESIS, AuditLog, AuditWriteError, audit_log_from
from hydra_umc_local_technician.orchestrator.dispatch import ToolDispatchError, dispatch_tool_request


def _request(tool, arguments, reason="check"):
    return build_tool_request_from_model_output(
        request_id="r-1", tool=tool, arguments=arguments, actor="tester", reason=reason,
    )


def _lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


class AuditLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "audit" / "audit.jsonl"

    def config(self, **kwargs):
        return OrchestratorConfig(storage_paths={"data": self.dir}, audit_log=AuditLog(self.path, **kwargs))

    def test_a_request_and_its_result_are_both_written_and_chained(self):
        result = dispatch_tool_request(_request("storage.usage", {"name": "data"}), self.config())
        lines = _lines(self.path)
        self.assertEqual([entry["event"] for entry in lines], ["request", "result"])
        self.assertEqual(lines[0]["tool"], "storage.usage")
        self.assertEqual(lines[0]["actor"], "tester")
        self.assertEqual(lines[0]["prev"], GENESIS)
        self.assertEqual(lines[1]["status"], result["status"])
        self.assertNotEqual(lines[1]["prev"], GENESIS)
        self.assertTrue(AuditLog(self.path).verify()[0])

    def test_a_refused_request_leaves_a_request_and_a_refusal(self):
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("storage.usage", {"name": "not-allowed"}), self.config())
        self.assertEqual([entry["event"] for entry in _lines(self.path)], ["request", "refused"])

    def test_secrets_in_arguments_and_reason_are_not_written(self):
        config = self.config()
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("storage.usage", {"name": "x password=hunter2"}, reason="token: abc123"), config)
        text = self.path.read_text(encoding="utf-8")
        self.assertNotIn("hunter2", text)
        self.assertNotIn("abc123", text)
        self.assertIn("[REDACTED]", text)

    def test_removing_or_editing_a_line_breaks_the_chain(self):
        config = self.config()
        for _ in range(3):
            dispatch_tool_request(_request("storage.usage", {"name": "data"}), config)
        original = self.path.read_bytes().decode("utf-8").splitlines()
        self.assertEqual(len(original), 6)
        self.path.write_bytes(("\n".join(original[:2] + original[3:]) + "\n").encode("utf-8"))
        ok, where = AuditLog(self.path).verify()
        self.assertFalse(ok)
        self.assertIn("audit.jsonl:3", where)
        edited = original[1].replace("result", "other")
        self.path.write_bytes(("\n".join(original[:1] + [edited] + original[2:]) + "\n").encode("utf-8"))
        self.assertFalse(AuditLog(self.path).verify()[0])

    def test_the_chain_continues_across_a_restart_and_a_rotation(self):
        first = AuditLog(self.path, max_bytes=1024, backups=3)
        for index in range(20):
            first.record({"event": "request", "requestId": f"r-{index}", "tool": "storage.usage"})
        self.assertTrue(Path(f"{self.path}.1").exists())
        self.assertLessEqual(self.path.stat().st_size, 1024)
        second = AuditLog(self.path, max_bytes=1024, backups=3)  # a new process picks the chain up
        second.record({"event": "request", "requestId": "after-restart", "tool": "storage.usage"})
        ok, summary = AuditLog(self.path, backups=3).verify()
        self.assertTrue(ok, summary)

    def test_only_the_configured_number_of_rotated_files_is_kept(self):
        log = AuditLog(self.path, max_bytes=1024, backups=2)
        for index in range(60):
            log.record({"event": "request", "requestId": f"r-{index}", "padding": "x" * 100})
        self.assertTrue(Path(f"{self.path}.2").exists())
        self.assertFalse(Path(f"{self.path}.3").exists())

    def test_nothing_runs_when_the_request_line_cannot_be_written(self):
        blocker = self.dir / "blocker"
        blocker.write_text("a file, not a folder", encoding="utf-8")
        config = OrchestratorConfig(storage_paths={"data": self.dir}, audit_log=AuditLog(blocker / "audit.jsonl"))
        with self.assertRaises(ToolDispatchError) as context:
            dispatch_tool_request(_request("storage.usage", {"name": "data"}), config)
        self.assertIn("not writable", str(context.exception))
        with self.assertRaises(AuditWriteError):
            config.audit_log.record({"event": "x"})

    def test_without_a_journal_nothing_is_written(self):
        config = OrchestratorConfig(storage_paths={"data": self.dir})
        dispatch_tool_request(_request("storage.usage", {"name": "data"}), config)
        self.assertFalse(self.path.exists())

    def test_the_journal_comes_from_a_path_or_the_environment_or_is_off(self):
        self.assertIsNone(audit_log_from(None, {}))
        self.assertEqual(audit_log_from(None, {"HYDRA_UMC_LOCAL_TECHNICIAN_AUDIT_LOG": str(self.path)}).path, self.path)
        self.assertEqual(audit_log_from("elsewhere.jsonl", {"HYDRA_UMC_LOCAL_TECHNICIAN_AUDIT_LOG": "x"}).path, Path("elsewhere.jsonl"))

    def test_bad_options_are_refused(self):
        for options in ({"max_bytes": 10}, {"backups": -1}, {"backups": True}, {"max_bytes": "big"}):
            with self.subTest(options), self.assertRaises(ValueError):
                AuditLog(self.path, **options)


class AuditCliTests(unittest.TestCase):
    def test_a_config_file_turns_the_journal_on_and_audit_verify_reads_it(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            journal = tmp / "audit.jsonl"
            config = tmp / "config.json"
            config.write_text(
                json.dumps({"storagePaths": {"data": str(tmp)}, "auditLog": {"path": str(journal), "backups": 2}}),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["tools", "call", "storage.usage", "--arg", "name=data", "--config", str(config)]), 0)
            self.assertEqual([entry["event"] for entry in _lines(journal)], ["request", "result"])
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(cli.main(["audit-verify", str(journal)]), 0)
            self.assertIn("AUDIT_CHAIN=PASS", out.getvalue())

    def test_a_broken_journal_makes_audit_verify_fail(self):
        with TemporaryDirectory() as tmp:
            journal = Path(tmp) / "audit.jsonl"
            log = AuditLog(journal)
            for index in range(3):
                log.record({"event": "request", "requestId": str(index)})
            lines = journal.read_text(encoding="utf-8").splitlines()
            journal.write_bytes(("\n".join([lines[0], lines[2]]) + "\n").encode("utf-8"))
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(cli.main(["audit-verify", str(journal)]), 1)
            self.assertIn("AUDIT_CHAIN=FAIL", out.getvalue())

    def test_an_unknown_audit_key_is_refused(self):
        with self.assertRaises(ValueError):
            cli._validate_config_shape({"auditLog": {"path": "a", "maxByte": 1}})
        with self.assertRaises(ValueError):
            cli._validate_config_shape({"auditLog": "a.jsonl"})


if __name__ == "__main__":
    unittest.main()
