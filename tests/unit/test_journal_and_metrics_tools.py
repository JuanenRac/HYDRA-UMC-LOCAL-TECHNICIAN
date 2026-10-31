# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_journal_and_metrics_tools.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""`journal.read` and `server.metrics`: both are closed by default and open only with the switch of the
configuration; once open they read only what the allow-list names, bounded and redacted."""
import io
import json
import threading
import unittest
from contextlib import redirect_stdout, redirect_stderr
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from hydra_umc_local_technician.cli import main
from hydra_umc_local_technician.knowledge.trust import build_tool_request_from_model_output
from hydra_umc_local_technician.orchestrator import dispatch as dispatch_module
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig, default_config
from hydra_umc_local_technician.orchestrator.dispatch import (
    ToolDispatchError, dispatch_tool_request, parse_prometheus_samples,
)


def _request(tool: str, arguments: dict):
    return build_tool_request_from_model_output(
        request_id=f"test-{tool}", tool=tool, arguments=arguments, actor="test", reason="unit test",
    )


class SwitchesAreClosedByDefault(unittest.TestCase):
    def test_the_default_configuration_has_both_tools_closed(self):
        config = default_config()
        self.assertFalse(config.journal_read_enabled)
        self.assertFalse(config.server_metrics_enabled)
        self.assertEqual(config.journal_units, ())
        self.assertEqual(config.metrics_targets, {})

    def test_journal_read_is_refused_while_closed_even_for_a_listed_unit(self):
        config = OrchestratorConfig(journal_units=("hydra-umc-server",))
        with mock.patch.object(dispatch_module.subprocess, "run") as run:
            with self.assertRaises(ToolDispatchError) as raised:
                dispatch_tool_request(_request("journal.read", {"name": "hydra-umc-server"}), config)
        self.assertIn("switched off", str(raised.exception))
        run.assert_not_called()

    def test_server_metrics_is_refused_while_closed_even_for_a_listed_target(self):
        config = OrchestratorConfig(metrics_targets={"server": "http://127.0.0.1:1/metrics"})
        with self.assertRaises(ToolDispatchError) as raised:
            dispatch_tool_request(_request("server.metrics", {"name": "server"}), config)
        self.assertIn("switched off", str(raised.exception))


class JournalRead(unittest.TestCase):
    def _config(self):
        return OrchestratorConfig(journal_read_enabled=True, journal_units=("hydra-umc-server",))

    def test_an_unlisted_unit_is_refused(self):
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("journal.read", {"name": "ssh"}), self._config())

    def test_reads_the_listed_unit_with_a_fixed_command_and_redacts(self):
        completed = SimpleNamespace(returncode=0, stdout=b"started\npassword=hunter2hunter2\nready\n", stderr=b"")
        with mock.patch.object(dispatch_module.shutil, "which", return_value="/usr/bin/journalctl"), \
                mock.patch.object(dispatch_module.subprocess, "run", return_value=completed) as run:
            result = dispatch_tool_request(_request("journal.read", {"name": "hydra-umc-server", "lines": 2}), self._config())
        command = run.call_args[0][0]
        self.assertEqual(command, ["/usr/bin/journalctl", "-u", "hydra-umc-server", "-n", "2", "-o", "cat", "--no-pager"])
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("hunter2hunter2", json.dumps(result["output"]))
        self.assertEqual(result["output"]["returned"], 2)

    def test_the_number_of_lines_is_capped(self):
        completed = SimpleNamespace(returncode=0, stdout=b"x\n", stderr=b"")
        with mock.patch.object(dispatch_module.shutil, "which", return_value="/usr/bin/journalctl"), \
                mock.patch.object(dispatch_module.subprocess, "run", return_value=completed) as run:
            dispatch_tool_request(_request("journal.read", {"name": "hydra-umc-server", "lines": 99999}), self._config())
        self.assertEqual(run.call_args[0][0][4], "500")

    def test_a_host_without_journalctl_says_so(self):
        with mock.patch.object(dispatch_module.shutil, "which", return_value=None):
            result = dispatch_tool_request(_request("journal.read", {"name": "hydra-umc-server"}), self._config())
        self.assertFalse(result["output"]["available"])
        self.assertEqual(result["output"]["lines"], [])

    def test_a_failing_journalctl_is_a_finding(self):
        completed = SimpleNamespace(returncode=1, stdout=b"", stderr=b"No journal files were found.")
        with mock.patch.object(dispatch_module.shutil, "which", return_value="/usr/bin/journalctl"), \
                mock.patch.object(dispatch_module.subprocess, "run", return_value=completed):
            result = dispatch_tool_request(_request("journal.read", {"name": "hydra-umc-server"}), self._config())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["output"]["returned"], 0)
        self.assertIn("No journal", result["output"]["reason"])


_PROMETHEUS = """# HELP hydra_up Is it up
# TYPE hydra_up gauge
hydra_up 1
hydra_cpu_load{core="0"} 12.5
hydra_text_sample{a="b"} not-a-number
other_metric 7
hydra_nan NaN
"""


class ParsePrometheus(unittest.TestCase):
    def test_keeps_only_finite_numeric_samples(self):
        samples, truncated = parse_prometheus_samples(_PROMETHEUS)
        self.assertFalse(truncated)
        self.assertEqual([s["metric"] for s in samples], ["hydra_up", "hydra_cpu_load", "other_metric"])
        self.assertEqual(samples[1]["labels"], '{core="0"}')

    def test_the_prefix_filters(self):
        samples, _ = parse_prometheus_samples(_PROMETHEUS, "hydra_cpu")
        self.assertEqual([s["metric"] for s in samples], ["hydra_cpu_load"])

    def test_the_count_is_bounded(self):
        text = "\n".join(f"m{i} {i}" for i in range(500))
        samples, truncated = parse_prometheus_samples(text)
        self.assertEqual(len(samples), 200)
        self.assertTrue(truncated)


class ServerMetrics(unittest.TestCase):
    def _serve(self, status=200, body=_PROMETHEUS):
        seen = {}

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - stdlib method name
                seen["client"] = self.headers.get("X-Hydra-Client")
                self.send_response(status)
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=5), server.server_close()))
        return server.server_address[1], seen

    def test_reads_samples_and_names_itself_to_the_server(self):
        port, seen = self._serve()
        config = OrchestratorConfig(server_metrics_enabled=True, metrics_targets={"server": f"http://127.0.0.1:{port}/metrics"})
        result = dispatch_tool_request(_request("server.metrics", {"name": "server", "prefix": "hydra_"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["output"]["reachable"])
        self.assertEqual([s["metric"] for s in result["output"]["samples"]], ["hydra_up", "hydra_cpu_load"])
        self.assertEqual(seen["client"], "technician")

    def test_an_unlisted_target_is_refused(self):
        config = OrchestratorConfig(server_metrics_enabled=True, metrics_targets={"server": "http://127.0.0.1:1/metrics"})
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("server.metrics", {"name": "other"}), config)

    def test_an_error_status_still_counts_as_an_answer(self):
        port, _ = self._serve(status=403, body="no")
        config = OrchestratorConfig(server_metrics_enabled=True, metrics_targets={"server": f"http://127.0.0.1:{port}/metrics"})
        result = dispatch_tool_request(_request("server.metrics", {"name": "server"}), config)
        self.assertTrue(result["output"]["reachable"])
        self.assertEqual(result["output"]["status_code"], 403)
        self.assertEqual(result["output"]["samples"], [])

    def test_a_scheme_other_than_http_is_never_opened(self):
        config = OrchestratorConfig(server_metrics_enabled=True, metrics_targets={"server": "file:///etc/passwd"})
        result = dispatch_tool_request(_request("server.metrics", {"name": "server"}), config)
        self.assertFalse(result["output"]["reachable"])

    def test_a_closed_port_is_a_finding(self):
        config = OrchestratorConfig(server_metrics_enabled=True, metrics_targets={"server": "http://127.0.0.1:1/metrics"})
        result = dispatch_tool_request(_request("server.metrics", {"name": "server"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["output"]["reachable"])


class ConfigFileSwitches(unittest.TestCase):
    def _call(self, tools_section, tool, *args):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"tools": tools_section}), encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["tools", "call", tool, *args, "--config", str(path)])
            return code, out.getvalue(), err.getvalue()

    def test_a_file_without_the_switch_keeps_the_tool_closed(self):
        code, _, err = self._call({"journalRead": {"units": ["hydra-umc-server"]}}, "journal.read", "--arg", "name=hydra-umc-server")
        self.assertNotEqual(code, 0)
        self.assertIn("switched off", err)

    def test_the_switch_must_be_a_real_boolean(self):
        code, _, err = self._call({"journalRead": {"enabled": "false", "units": ["x"]}}, "journal.read", "--arg", "name=x")
        self.assertEqual(code, 2)
        self.assertIn("invalid --config", err)

    def test_unknown_keys_in_tools_are_refused(self):
        code, _, err = self._call({"shellExec": {"enabled": True}}, "journal.read", "--arg", "name=x")
        self.assertEqual(code, 2)
        self.assertIn("invalid --config", err)

    def test_an_open_switch_reaches_the_tool(self):
        with mock.patch.object(dispatch_module.shutil, "which", return_value=None):
            code, out, _ = self._call(
                {"journalRead": {"enabled": True, "units": ["hydra-umc-server"]}}, "journal.read", "--arg", "name=hydra-umc-server")
        self.assertEqual(code, 0)
        self.assertIn("journalctl not found", out)


if __name__ == "__main__":
    unittest.main()
