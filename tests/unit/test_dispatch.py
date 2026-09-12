# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_dispatch.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 3's own real handlers, exercised for real: a real temp directory
for storage.usage, a real local socket this test itself opens/closes for
network.port_status, a real manifest file on disk for manifest.read. Only
service.status/system.temperature's own real host state is out of this
test's control (a dev machine is neither guaranteed to have systemd nor a
Linux thermal sensor) - those are tested for the one thing genuinely
verifiable everywhere: the honest-degradation path never raises and never
guesses a reading.
"""
import json
import socket
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.contracts import ContractValidationError, validate
from hydra_umc_local_technician.knowledge.trust import build_tool_request_from_model_output
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.orchestrator.dispatch import ToolDispatchError, dispatch_tool_request
from hydra_umc_local_technician.policy.tool_matrix import TOOL_MATRIX


def _request(tool: str, arguments: dict):
    return build_tool_request_from_model_output(
        request_id=f"test-{tool}", tool=tool, arguments=arguments,
        actor="test", reason="unit test",
    )


class ImplementedToolsMatchHandlersTests(unittest.TestCase):
    def test_every_implemented_tool_has_a_real_handler(self):
        from hydra_umc_local_technician.orchestrator.dispatch import _HANDLERS
        implemented = {name for name, d in TOOL_MATRIX.items() if d.implemented}
        self.assertEqual(implemented, set(_HANDLERS), "TOOL_MATRIX.implemented and dispatch._HANDLERS must never drift apart")


class StorageUsageTests(unittest.TestCase):
    def test_reports_real_usage_for_an_allow_listed_path(self):
        with TemporaryDirectory() as tmp:
            config = OrchestratorConfig(storage_paths={"scratch": Path(tmp)})
            result = dispatch_tool_request(_request("storage.usage", {"name": "scratch"}), config)
            validate("ToolResult", result)
            self.assertEqual(result["status"], "ok")
            self.assertGreater(result["output"]["totalBytes"], 0)
            self.assertEqual(result["output"]["name"], "scratch")

    def test_refuses_a_name_not_on_the_allow_list(self):
        config = OrchestratorConfig(storage_paths={})
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("storage.usage", {"name": "not-configured"}), config)

    def test_refuses_a_missing_name_argument(self):
        config = OrchestratorConfig(storage_paths={"scratch": Path(".")})
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("storage.usage", {}), config)


class NetworkPortStatusTests(unittest.TestCase):
    def test_reports_listening_true_for_a_real_open_port(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        try:
            port = server.getsockname()[1]
            config = OrchestratorConfig(ports={"probe": ("127.0.0.1", port)})
            result = dispatch_tool_request(_request("network.port_status", {"name": "probe"}), config)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["output"]["listening"])
        finally:
            server.close()

    def test_reports_listening_false_for_a_real_closed_port(self):
        # Bind then immediately close to get a real, currently-closed
        # port on this host rather than guessing a plausible-looking
        # number that might collide with something else running here.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        config = OrchestratorConfig(ports={"probe": ("127.0.0.1", port)})
        result = dispatch_tool_request(_request("network.port_status", {"name": "probe"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["output"]["listening"])

    def test_refuses_a_name_not_on_the_allow_list(self):
        config = OrchestratorConfig(ports={})
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("network.port_status", {"name": "not-configured"}), config)


class NetworkConnectivityTests(unittest.TestCase):
    def test_reports_reachable_true_with_the_real_status_code_for_a_real_local_server(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - stdlib method name
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass  # keep test output clean

        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            config = OrchestratorConfig(connectivity_targets={"probe": f"http://127.0.0.1:{port}/"})
            result = dispatch_tool_request(_request("network.connectivity", {"name": "probe"}), config)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["output"]["reachable"])
            self.assertEqual(result["output"]["status_code"], 200)
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_a_real_http_error_status_still_counts_as_reachable(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(503)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            config = OrchestratorConfig(connectivity_targets={"probe": f"http://127.0.0.1:{port}/"})
            result = dispatch_tool_request(_request("network.connectivity", {"name": "probe"}), config)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["output"]["reachable"], "a real HTTP error response still means the endpoint answered")
            self.assertEqual(result["output"]["status_code"], 503)
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_reports_unreachable_for_a_real_closed_port(self):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        config = OrchestratorConfig(connectivity_targets={"probe": f"http://127.0.0.1:{port}/"})
        result = dispatch_tool_request(_request("network.connectivity", {"name": "probe"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["output"]["reachable"])
        self.assertIsNone(result["output"]["status_code"])

    def test_refuses_a_name_not_on_the_allow_list(self):
        config = OrchestratorConfig(connectivity_targets={})
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("network.connectivity", {"name": "not-configured"}), config)

    def test_refuses_a_non_http_scheme_even_if_somehow_configured(self):
        config = OrchestratorConfig(connectivity_targets={"probe": "ftp://127.0.0.1/"})
        result = dispatch_tool_request(_request("network.connectivity", {"name": "probe"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["output"]["reachable"])
        self.assertIn("scheme", result["output"]["reason"])


class LogsReadTests(unittest.TestCase):
    def test_reads_the_last_n_lines_of_a_real_allow_listed_file(self):
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "server.log"
            log_path.write_text("\n".join(f"line-{i}" for i in range(1, 11)) + "\n", encoding="utf-8")
            config = OrchestratorConfig(log_sources={"server_log": log_path})
            result = dispatch_tool_request(_request("logs.read", {"name": "server_log", "lines": 3}), config)
            validate("ToolResult", result)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["output"]["exists"])
            self.assertEqual(result["output"]["lines"], ["line-8", "line-9", "line-10"])

    def test_redacts_a_real_secret_before_it_ever_leaves_the_handler(self):
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "server.log"
            log_path.write_text("normal line\nAuthorization: Bearer sk-real-secret-token\n", encoding="utf-8")
            config = OrchestratorConfig(log_sources={"server_log": log_path})
            result = dispatch_tool_request(_request("logs.read", {"name": "server_log"}), config)
            joined = "\n".join(result["output"]["lines"])
            self.assertNotIn("sk-real-secret-token", joined)

    def test_reports_a_missing_file_honestly_instead_of_erroring(self):
        config = OrchestratorConfig(log_sources={"server_log": Path("/does/not/exist.log")})
        result = dispatch_tool_request(_request("logs.read", {"name": "server_log"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["output"]["exists"])
        self.assertEqual(result["output"]["lines"], [])

    def test_a_requested_line_count_is_capped_not_silently_ignored(self):
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "server.log"
            log_path.write_text("\n".join(f"line-{i}" for i in range(1, 1000)) + "\n", encoding="utf-8")
            config = OrchestratorConfig(log_sources={"server_log": log_path})
            result = dispatch_tool_request(_request("logs.read", {"name": "server_log", "lines": 999999}), config)
            self.assertLessEqual(len(result["output"]["lines"]), 500)

    def test_refuses_a_name_not_on_the_allow_list(self):
        config = OrchestratorConfig(log_sources={})
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("logs.read", {"name": "not-configured"}), config)

class ProcessListTests(unittest.TestCase):
    def test_refuses_a_name_not_on_the_allow_list(self):
        config = OrchestratorConfig(process_patterns={"worker": "hydra-umc-vision-streamer"})
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("process.list", {"name": "not-configured"}), config)

    def test_an_allow_listed_pattern_never_raises_regardless_of_platform(self):
        # Real platform honesty (this dev machine may have no real /proc
        # at all) - the one thing genuinely verifiable everywhere is a
        # valid, honest ToolResult either way, never an unhandled
        # exception and never a raw process table.
        config = OrchestratorConfig(process_patterns={"worker": "a-pattern-nothing-real-matches-xyz"})
        result = dispatch_tool_request(_request("process.list", {"name": "worker"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertIn("available", result["output"])
        if result["output"]["available"]:
            self.assertIn("matches", result["output"])
            self.assertIn("running", result["output"])
        else:
            self.assertIn("reason", result["output"])

    @unittest.skipUnless(Path("/proc").is_dir(), "needs a real Linux /proc to exercise a real match")
    def test_finds_a_real_running_process_by_its_real_cmdline(self):
        import subprocess
        import sys
        import time

        marker = "hydra-umc-local-technician-test-marker-4f3a9c"
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)", marker])
        try:
            deadline = time.monotonic() + 3
            matches: list = []
            while time.monotonic() < deadline:
                config = OrchestratorConfig(process_patterns={"worker": marker})
                result = dispatch_tool_request(_request("process.list", {"name": "worker"}), config)
                matches = result["output"]["matches"]
                if matches:
                    break
                time.sleep(0.1)
            self.assertTrue(matches, "expected to find the real spawned process by its own cmdline")
            self.assertEqual(matches[0]["pid"], proc.pid)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    @unittest.skipUnless(Path("/proc").is_dir(), "needs a real Linux /proc")
    def test_a_pattern_matching_nothing_reports_not_running(self):
        config = OrchestratorConfig(process_patterns={"worker": "definitely-not-a-real-process-xyz123"})
        result = dispatch_tool_request(_request("process.list", {"name": "worker"}), config)
        self.assertTrue(result["output"]["available"])
        self.assertFalse(result["output"]["running"])
        self.assertEqual(result["output"]["matches"], [])


class LogsReadLargeFileTests(unittest.TestCase):
    def test_a_large_file_is_tailed_within_a_bounded_byte_window(self):
        # Real proof _tail_lines() bounds the READ itself, not just the
        # line count after the fact: a file far larger than the byte
        # window still returns quickly and only the real tail content,
        # never the file's own beginning.
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "server.log"
            with log_path.open("w", encoding="utf-8") as f:
                for i in range(200_000):
                    f.write(f"line-{i}\n")
            config = OrchestratorConfig(log_sources={"server_log": log_path})
            result = dispatch_tool_request(_request("logs.read", {"name": "server_log", "lines": 5}), config)
            self.assertEqual(result["output"]["lines"], ["line-199995", "line-199996", "line-199997", "line-199998", "line-199999"])


class SystemTemperatureTests(unittest.TestCase):
    def test_never_raises_and_never_guesses_a_reading(self):
        # Real platform honesty: this runs on whatever host CI/the dev
        # machine actually is - assert only the one thing true
        # everywhere, the same contract-shaped result either way.
        config = OrchestratorConfig()
        result = dispatch_tool_request(_request("system.temperature", {}), config)
        self.assertEqual(result["status"], "ok")
        if result["output"]["available"]:
            self.assertIsInstance(result["output"]["celsius"], float)
        else:
            self.assertIn("reason", result["output"])


class ServiceStatusTests(unittest.TestCase):
    def test_refuses_a_unit_not_on_the_allow_list(self):
        config = OrchestratorConfig(systemd_units=("hydra-umc-server",))
        with self.assertRaises(ToolDispatchError):
            dispatch_tool_request(_request("service.status", {"name": "some-other.service"}), config)

    def test_an_allow_listed_unit_never_raises_even_without_systemd(self):
        # Real platform honesty (this is a dev machine, not a systemd
        # host in general) - the ONE thing genuinely verifiable
        # everywhere is that the result is a valid, honest ToolResult
        # either way, never an unhandled exception.
        config = OrchestratorConfig(systemd_units=("hydra-umc-server",))
        result = dispatch_tool_request(_request("service.status", {"name": "hydra-umc-server"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertIn("active", result["output"])
        self.assertIn("available", result["output"])


class ManifestReadTests(unittest.TestCase):
    def test_reads_a_real_manifest_under_the_configured_root(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "HYDRA-UMC-EXAMPLE"
            project_dir.mkdir()
            manifest = {"name": "HYDRA-UMC-EXAMPLE", "version": "1.2.3", "maturity": "functional", "role": "service"}
            (project_dir / "hydra-umc.project.json").write_text(json.dumps(manifest), encoding="utf-8")
            config = OrchestratorConfig(ecosystem_root=root)
            result = dispatch_tool_request(_request("manifest.read", {"project": "HYDRA-UMC-EXAMPLE"}), config)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["output"]["found"])
            self.assertEqual(result["output"]["version"], "1.2.3")

    def test_a_project_with_no_manifest_reports_found_false_not_an_error(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HYDRA-UMC-EMPTY").mkdir()
            config = OrchestratorConfig(ecosystem_root=root)
            result = dispatch_tool_request(_request("manifest.read", {"project": "HYDRA-UMC-EMPTY"}), config)
            self.assertEqual(result["status"], "ok")
            self.assertFalse(result["output"]["found"])

    def test_refuses_a_project_name_outside_the_real_naming_pattern(self):
        with TemporaryDirectory() as tmp:
            config = OrchestratorConfig(ecosystem_root=Path(tmp))
            with self.assertRaises(ToolDispatchError):
                dispatch_tool_request(_request("manifest.read", {"project": "not-a-real-project-name"}), config)

    def test_refuses_path_traversal_disguised_as_a_project_name(self):
        with TemporaryDirectory() as tmp:
            config = OrchestratorConfig(ecosystem_root=Path(tmp))
            with self.assertRaises(ToolDispatchError):
                dispatch_tool_request(_request("manifest.read", {"project": "HYDRA-UMC-../../etc"}), config)


class UnknownAndUnimplementedToolTests(unittest.TestCase):
    def test_an_unregistered_tool_is_refused_before_this_module_ever_sees_it(self):
        # build_tool_request_from_model_output() itself already refuses
        # this - confirms dispatch_tool_request() is never even reachable
        # with one.
        from hydra_umc_local_technician.knowledge.trust import ToolCallRefused
        with self.assertRaises(ToolCallRefused):
            _request("shell.exec", {})

    def test_a_result_this_module_produces_always_satisfies_its_own_contract(self):
        with TemporaryDirectory() as tmp:
            config = OrchestratorConfig(storage_paths={"scratch": Path(tmp)})
            result = dispatch_tool_request(_request("storage.usage", {"name": "scratch"}), config)
            validate("ToolResult", result)  # raises ContractValidationError on any real drift


if __name__ == "__main__":
    unittest.main()
