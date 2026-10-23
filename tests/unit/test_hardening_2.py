# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - outbox durability, process matching, service status and the execution policy
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from hydra_umc_local_technician.escalation import outbox as outbox_module
from hydra_umc_local_technician.escalation.outbox import CONFLICT, DUPLICATE, QUEUED, EscalationOutbox
from hydra_umc_local_technician.knowledge.trust import ToolRequest, build_tool_request_from_model_output
from hydra_umc_local_technician.orchestrator import dispatch as dispatch_module
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.orchestrator.dispatch import (
    ToolDispatchError,
    _list_proc_matches,
    _names_the_program,
    dispatch_tool_request,
)
from hydra_umc_local_technician.policy.execution_mode import ExecutionMode
from hydra_umc_local_technician.policy.risk_levels import RiskLevel
from hydra_umc_local_technician.policy.tool_matrix import TOOL_MATRIX, ToolDescriptor


class OutboxDurabilityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name)
        self.outbox = EscalationOutbox(self.directory)

    def test_a_new_id_is_queued_and_the_same_payload_again_is_a_duplicate(self):
        self.assertEqual(self.outbox.enqueue("e1", {"a": 1}), QUEUED)
        self.assertEqual(self.outbox.enqueue("e1", {"a": 1}), DUPLICATE)
        self.assertEqual(len(self.outbox.pending()), 1)

    def test_the_same_id_with_another_payload_keeps_the_first_and_sets_the_second_aside(self):
        self.outbox.enqueue("e1", {"a": 1})
        self.assertEqual(self.outbox.enqueue("e1", {"a": 2}), CONFLICT)
        self.assertEqual(self.outbox.pending()[0].payload, {"a": 1}, "the first payload wins and is not replaced")
        aside = sorted((self.directory / "corrupt").glob("e1.conflict*.json"))
        self.assertEqual([json.loads(p.read_text(encoding="utf-8")) for p in aside], [{"a": 2}])

    def test_an_id_already_sent_is_not_queued_again(self):
        self.outbox.enqueue("e1", {"a": 1})
        self.outbox.mark_sent("e1")
        self.assertEqual(self.outbox.enqueue("e1", {"a": 1}), DUPLICATE)
        self.assertEqual(self.outbox.enqueue("e1", {"a": 9}), CONFLICT)
        self.assertEqual(self.outbox.pending(), [])

    def test_two_processes_queueing_one_id_cannot_both_win(self):
        # the other process creates the entry between this one's check and its link
        real_link = os.link

        def other_process_got_there_first(source, destination, *args, **kwargs):
            Path(destination).write_text(json.dumps({"from": "the other process"}), encoding="utf-8")
            return real_link(source, destination, *args, **kwargs)  # now fails: FileExistsError

        with mock.patch.object(outbox_module.os, "link", other_process_got_there_first):
            self.assertEqual(self.outbox.enqueue("race", {"from": "this process"}), CONFLICT)
        self.assertEqual(self.outbox.pending()[0].payload, {"from": "the other process"})
        self.assertEqual(list((self.directory / "pending").glob("*.tmp")), [], "no temporary file is left")

    def test_a_file_system_without_hard_links_still_queues(self):
        with mock.patch.object(outbox_module.os, "link", side_effect=OSError("no hard links here")):
            self.assertEqual(self.outbox.enqueue("e1", {"a": 1}), QUEUED)
        self.assertEqual(self.outbox.pending()[0].payload, {"a": 1})
        self.assertEqual(list((self.directory / "pending").glob("*.tmp")), [])

    def test_old_temporaries_of_a_dead_process_are_set_aside_young_ones_stay(self):
        old = self.directory / "pending" / "tmpold.tmp"
        young = self.directory / "pending" / "tmpyoung.tmp"
        old.write_text("{", encoding="utf-8")
        young.write_text("{", encoding="utf-8")
        past = time.time() - outbox_module.STALE_TEMPORARY_SECONDS - 5
        os.utime(old, (past, past))
        EscalationOutbox(self.directory)  # opening the outbox does it
        self.assertFalse(old.exists())
        self.assertTrue((self.directory / "corrupt" / "tmpold.tmp").exists(), "moved, not deleted")
        self.assertTrue(young.exists(), "a process may be writing it right now")

    def test_marking_sent_never_overwrites_the_record_of_what_was_sent(self):
        self.outbox.enqueue("e1", {"a": 1})
        self.outbox.mark_sent("e1")
        sent = self.directory / "sent" / "e1.json"
        before = sent.read_text(encoding="utf-8")
        (self.directory / "pending" / "e1.json").write_text(json.dumps({"a": "again"}), encoding="utf-8")
        self.outbox.mark_sent("e1")
        self.assertEqual(sent.read_text(encoding="utf-8"), before)
        self.assertEqual(self.outbox.pending(), [])
        self.assertTrue(list((self.directory / "corrupt").glob("e1*.json")), "the pending copy was set aside, not lost")

    def test_whatever_the_transport_raises_nothing_is_confirmed_and_the_item_stays(self):
        self.outbox.enqueue("e1", {"a": 1})
        self.outbox.enqueue("e2", {"a": 2})

        def boom(item):
            raise RuntimeError("the transport library failed in an unexpected way")

        self.assertEqual(self.outbox.flush(boom), 0)
        self.assertEqual([item.escalation_id for item in self.outbox.pending()], ["e1", "e2"])


class ProcessMatchingTests(unittest.TestCase):
    PATTERN = "hydra-umc-vision-streamer"

    def test_the_program_itself_matches(self):
        for arguments in (
            [self.PATTERN, "stream", "serve"],
            [f"/opt/hydra-umc/vision-streamer/.venv/bin/{self.PATTERN}", "stream", "serve", "--port", "8100"],
        ):
            self.assertTrue(_names_the_program(arguments, self.PATTERN), arguments)

    def test_an_interpreter_running_the_program_matches_by_its_script_or_module(self):
        self.assertTrue(_names_the_program(["/usr/bin/python3", f"/opt/x/bin/{self.PATTERN}", "serve"], self.PATTERN))
        self.assertTrue(_names_the_program(["python3", "-u", f"/opt/x/{self.PATTERN}.py"], self.PATTERN))
        self.assertTrue(_names_the_program(["python3", "-m", "hydra-umc-vision-streamer.main"], self.PATTERN))
        self.assertTrue(_names_the_program(["node", f"{self.PATTERN}/server.js"], self.PATTERN))

    def test_a_process_that_only_mentions_the_name_does_not_match(self):
        for arguments in (
            ["grep", self.PATTERN],
            ["journalctl", "-u", self.PATTERN, "-n", "50"],
            ["tail", "-f", f"/var/log/{self.PATTERN}.log"],
            ["vim", f"{self.PATTERN}.service"],
            ["python3", "-c", f"print('{self.PATTERN}')"],
            ["bash", "-c", f"{self.PATTERN} stream serve"],
            ["python3", "unrelated.py", self.PATTERN],
            [],
        ):
            self.assertFalse(_names_the_program(arguments, self.PATTERN), arguments)

    def test_the_proc_scan_uses_it_and_never_reports_its_own_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            entries = {
                "101": [self.PATTERN, "stream", "serve", "--token", "s3cretvalue123456"],
                "102": ["grep", self.PATTERN],
                "103": ["python3", f"/opt/{self.PATTERN}/run.py"],
                str(os.getpid()): [self.PATTERN],
                "notapid": [self.PATTERN],
            }
            for name, arguments in entries.items():
                (proc / name).mkdir()
                (proc / name / "cmdline").write_bytes("\x00".join(arguments).encode("utf-8") + b"\x00")
            matches, truncated = _list_proc_matches(self.PATTERN, proc)
        self.assertFalse(truncated)
        self.assertEqual([m["pid"] for m in matches], [101, 103])
        self.assertNotIn("s3cretvalue123456", json.dumps(matches), "the command line is redacted")


def _completed(stdout="", returncode=0, stderr=""):
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


def _request(tool, arguments):
    if tool in TOOL_MATRIX:
        return build_tool_request_from_model_output(request_id=f"test-{tool}", tool=tool, arguments=arguments, actor="test", reason="unit test")
    # a tool the matrix does not know cannot be built by the checked path; the dispatcher is handed it directly
    return ToolRequest(
        schema_version="1.0", request_id=f"test-{tool}", tool=tool, arguments=arguments,
        risk_level=RiskLevel.REVERSIBLE_OPERATION, actor="test", reason="unit test",
    )


class ServiceStatusDetailTests(unittest.TestCase):
    CONFIG = OrchestratorConfig(systemd_units=("hydra-umc-server",))

    def run_tool(self, side_effect):
        with mock.patch.object(dispatch_module.shutil, "which", return_value="/bin/systemctl"), \
                mock.patch.object(dispatch_module.subprocess, "run", side_effect=side_effect) as runner:
            result = dispatch_tool_request(_request("service.status", {"name": "hydra-umc-server"}), self.CONFIG)
        return result, runner

    def test_show_gives_the_state_the_result_and_the_restarts(self):
        shown = "ActiveState=failed\nSubState=failed\nResult=exit-code\nNRestarts=7\nExecMainStatus=1\n"
        result, runner = self.run_tool([_completed(shown)])
        output = result["output"]
        self.assertEqual((output["active"], output["activeState"], output["subState"], output["result"]), (False, "failed", "failed", "exit-code"))
        self.assertEqual((output["restarts"], output["mainExitStatus"]), (7, 1))
        command = runner.call_args_list[0].args[0]
        self.assertEqual(command[:2], ["/bin/systemctl", "show"])
        self.assertIn("--", command)
        self.assertEqual(command[-1], "hydra-umc-server", "the unit comes after `--`, so it cannot be read as an option")

    def test_an_active_unit_is_active(self):
        shown = "ActiveState=active\nSubState=running\nResult=success\nNRestarts=0\nExecMainStatus=0\n"
        result, _ = self.run_tool([_completed(shown)])
        self.assertTrue(result["output"]["active"])
        self.assertEqual(result["output"]["restarts"], 0)

    def test_values_that_are_not_plain_numbers_become_none_not_text(self):
        shown = "ActiveState=active\nNRestarts=[not set]\nExecMainStatus=1234567890123\n"
        result, _ = self.run_tool([_completed(shown)])
        self.assertIsNone(result["output"]["restarts"])
        self.assertIsNone(result["output"]["mainExitStatus"])

    def test_a_systemctl_that_cannot_show_falls_back_to_is_active(self):
        result, runner = self.run_tool([_completed("", returncode=1, stderr="unknown"), _completed("active\n", 0)])
        self.assertTrue(result["output"]["active"])
        self.assertEqual(runner.call_args_list[1].args[0][1:], ["is-active", "--", "hydra-umc-server"])
        self.assertNotIn("activeState", result["output"])


class ExecutionPolicyOnTheRealPathTests(unittest.TestCase):
    def test_the_default_mode_is_diagnosis_only(self):
        self.assertIs(OrchestratorConfig().execution_mode, ExecutionMode.DIAGNOSIS_ONLY)

    def test_every_registered_tool_still_runs_because_all_are_read_only(self):
        # nothing the policy now stands in front of may stop what exists
        config = OrchestratorConfig(systemd_units=("hydra-umc-server",))
        with mock.patch.object(dispatch_module.shutil, "which", return_value=None):
            result = dispatch_tool_request(_request("service.status", {"name": "hydra-umc-server"}), config)
        self.assertEqual(result["status"], "ok")

    def test_a_tool_above_observe_is_refused_before_its_handler_runs(self):
        descriptor = ToolDescriptor(
            name="service.restart", description="restart a unit", risk_level=RiskLevel.REVERSIBLE_OPERATION, implemented=True,
        )
        called = []
        with mock.patch.object(dispatch_module, "lookup_tool", return_value=descriptor), \
                mock.patch.dict(dispatch_module._HANDLERS, {"service.restart": lambda config, arguments: called.append(1)}):
            for mode in ExecutionMode:
                config = OrchestratorConfig(execution_mode=mode)
                with self.assertRaises(ToolDispatchError) as raised:
                    dispatch_tool_request(_request("service.restart", {"name": "x"}), config)
                self.assertIn("execution policy", str(raised.exception))
        self.assertEqual(called, [], "the handler never ran")


if __name__ == "__main__":
    unittest.main()
