# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_hardening.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Behaviour at the edges of the OBSERVE tools, the knowledge index, the CLI
and the escalation outbox: a redirect is not followed, a command line is
redacted, one unreadable file does not break a search, a corrupt queue entry
does not block the queue behind it."""
import io
import json
import os
import threading
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.cli import main
from hydra_umc_local_technician.escalation.evidence import ObservedResult, assemble_evidence_bundle
from hydra_umc_local_technician.escalation.outbox import EscalationOutbox
from hydra_umc_local_technician.knowledge import index as knowledge_index
from hydra_umc_local_technician.knowledge.trust import build_tool_request_from_model_output
from hydra_umc_local_technician.orchestrator import dispatch as dispatch_module
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.orchestrator.dispatch import dispatch_tool_request


def _request(tool: str, arguments: dict):
    return build_tool_request_from_model_output(
        request_id=f"test-{tool}", tool=tool, arguments=arguments, actor="test", reason="unit test",
    )


class _Server:
    def __init__(self, handler):
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self.server.server_address[1]

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class ConnectivityRedirectTests(unittest.TestCase):
    def test_a_redirect_is_reported_and_never_followed(self):
        followed = []

        class Target(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                followed.append(self.path)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        with _Server(Target) as target_port:
            class Redirector(BaseHTTPRequestHandler):
                def do_GET(self):  # noqa: N802
                    self.send_response(302)
                    self.send_header("Location", f"http://127.0.0.1:{target_port}/elsewhere")
                    self.end_headers()

                def log_message(self, *args):
                    pass

            with _Server(Redirector) as port:
                config = OrchestratorConfig(connectivity_targets={"probe": f"http://127.0.0.1:{port}/"})
                result = dispatch_tool_request(_request("network.connectivity", {"name": "probe"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["output"]["reachable"])
        self.assertEqual(result["output"]["status_code"], 302)
        self.assertEqual(followed, [], "the redirect target must never be contacted")

    def test_a_connection_dropped_mid_response_is_unreachable_not_an_error(self):
        class Rude(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.wfile.write(b"not http at all\r\n\r\n")

            def log_message(self, *args):
                pass

        with _Server(Rude) as port:
            config = OrchestratorConfig(connectivity_targets={"probe": f"http://127.0.0.1:{port}/"})
            result = dispatch_tool_request(_request("network.connectivity", {"name": "probe"}), config)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["output"]["reachable"])


class ProcessListRedactionTests(unittest.TestCase):
    def _proc_tree(self, root: Path, entries: dict[str, bytes]) -> None:
        for pid, cmdline in entries.items():
            (root / pid).mkdir()
            (root / pid / "cmdline").write_bytes(cmdline)

    def test_secrets_in_a_command_line_are_redacted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._proc_tree(root, {"101": b"streamer\x00--token\x00hunter2-token-value\x00--password=swordfish\x00--port\x008080"})
            matches, truncated = dispatch_module._list_proc_matches("streamer", root)
        self.assertFalse(truncated)
        self.assertEqual(len(matches), 1)
        line = matches[0]["cmdline"]
        self.assertNotIn("swordfish", line)
        self.assertIn("--port 8080", line)

    def test_the_technicians_own_process_is_never_a_match(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._proc_tree(root, {str(os.getpid()): b"python\x00streamer", "202": b"streamer\x00serve"})
            matches, _ = dispatch_module._list_proc_matches("streamer", root)
        self.assertEqual([m["pid"] for m in matches], [202])

    def test_an_unreadable_process_entry_is_skipped(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "303").mkdir()  # no cmdline file: the process vanished
            self._proc_tree(root, {"404": b"streamer"})
            matches, _ = dispatch_module._list_proc_matches("streamer", root)
        self.assertEqual([m["pid"] for m in matches], [404])


class ManifestReadBoundsTests(unittest.TestCase):
    def _read(self, raw: bytes):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HYDRA-UMC-EXAMPLE").mkdir()
            (root / "HYDRA-UMC-EXAMPLE" / "hydra-umc.project.json").write_bytes(raw)
            config = OrchestratorConfig(ecosystem_root=root)
            return dispatch_tool_request(_request("manifest.read", {"project": "HYDRA-UMC-EXAMPLE"}), config)

    def test_a_manifest_that_is_not_utf8_is_reported_not_found(self):
        result = self._read(b'{"name": "\xff\xfe"}')
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["output"]["found"])

    def test_an_oversized_manifest_is_refused(self):
        result = self._read(b'{"name": "' + b"a" * (dispatch_module._MANIFEST_MAX_BYTES + 1) + b'"}')
        self.assertFalse(result["output"]["found"])
        self.assertIn("larger", result["output"]["reason"])

    def test_fields_that_are_not_short_strings_are_reported_absent(self):
        manifest = {"name": {"nested": "object"}, "version": "1" * 500, "maturity": 7, "role": "service"}
        result = self._read(json.dumps(manifest).encode("utf-8"))
        output = result["output"]
        self.assertTrue(output["found"])
        self.assertIsNone(output["name"])
        self.assertIsNone(output["version"])
        self.assertIsNone(output["maturity"])
        self.assertEqual(output["role"], "service")


class UpdatePendingFourPartVersionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        root = Path(self.tmpdir.name)
        (root / "HYDRA-UMC-EXAMPLE").mkdir()
        (root / "HYDRA-UMC-EXAMPLE" / "hydra-umc.project.json").write_text("{}", encoding="utf-8")
        self.config = OrchestratorConfig(ecosystem_root=root)

    def _run(self, local: str, remote):
        from test_dispatch import _FakeUpdaterEntry, _FakeUpdaterManifest, _FakeUpdaterRemoteStatus, _FakeUpdaterVersion

        patched = unittest.mock.patch.multiple(
            dispatch_module,
            _HAS_UPDATE_CHECK=True,
            _updater_parse_manifest=lambda raw, expected_name: _FakeUpdaterManifest(local),
            _updater_entry_from_manifest=lambda manifest: _FakeUpdaterEntry("HYDRA-UMC-EXAMPLE"),
            _updater_fetch_all=lambda entries: {"HYDRA-UMC-EXAMPLE": _FakeUpdaterRemoteStatus(version=remote(_FakeUpdaterVersion))},
            _UpdaterVersion=_FakeUpdaterVersion,
            _UpdaterManifestValidationError=ValueError,
        )
        with patched:
            return dispatch_tool_request(_request("update.pending", {"project": "HYDRA-UMC-EXAMPLE"}), self.config)

    def test_a_four_component_local_version_is_understood(self):
        result = self._run("0.8.0.0", lambda v: v(0, 8, 0, 1, has_build=True))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["output"]["local_version"], "0.8.0.0")
        self.assertTrue(result["output"]["pending"])

    def test_an_unreadable_local_version_is_reported_not_a_tool_error(self):
        result = self._run("not.a.version", lambda v: v(0, 8, 0))
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["output"]["found"])
        self.assertIsNone(result["output"]["pending"])


class KnowledgeSearchEdgeTests(unittest.TestCase):
    def test_one_file_that_is_not_utf8_does_not_break_the_index(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "good.md").write_text("# Good\n\nThe camera worker restarts itself.\n", encoding="utf-8")
            (root / "latin1.md").write_bytes("# Caf\xe9\n\nr\xe9sum\xe9\n".encode("latin-1"))
            result = knowledge_index.ingest_source_directory(root)
        self.assertEqual(result.indexed_sources, ("good.md",))
        self.assertEqual(result.skipped_sources, ("latin1.md",))

    def test_a_symlink_pointing_outside_the_root_is_skipped_not_read(self):
        with TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside"
            outside.mkdir()
            (outside / "secret.md").write_text("# Secret\n\nnever indexed\n", encoding="utf-8")
            root = Path(tmp) / "root"
            root.mkdir()
            (root / "good.md").write_text("# Good\n\nplain text\n", encoding="utf-8")
            try:
                (root / "link.md").symlink_to(outside / "secret.md")
            except (OSError, NotImplementedError):
                self.skipTest("this platform does not allow creating symlinks here")
            result = knowledge_index.ingest_source_directory(root)
        self.assertEqual(result.indexed_sources, ("good.md",))
        self.assertIn("link.md", result.skipped_sources)
        self.assertFalse(any("never indexed" in chunk.text for chunk in result.chunks))

    def test_a_search_result_is_redacted_and_bounded(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            padding = "filler " * 2000
            (root / "runbook.md").write_text(
                "# Restart\n\nrestart procedure\nDB_PASSWORD=swordfish-12345\n" + padding, encoding="utf-8",
            )
            config = OrchestratorConfig(knowledge_sources={"docs": root})
            result = dispatch_tool_request(_request("knowledge.search", {"source": "docs", "query": "restart procedure"}), config)
        hit = result["output"]["results"][0]
        self.assertNotIn("swordfish", hit["text"])
        self.assertLessEqual(len(hit["text"]), dispatch_module._KNOWLEDGE_SEARCH_MAX_EXCERPT_CHARS)
        self.assertTrue(hit["textTruncated"])


class CliConfigErrorTests(unittest.TestCase):
    def _call(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_a_config_that_is_not_json_is_refused_in_one_line(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{ not json", encoding="utf-8")
            code, _, err = self._call(["tools", "call", "storage.usage", "--arg", "name=x", "--config", str(path)])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: invalid --config", err)

    def test_a_config_with_the_wrong_shape_is_refused(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"ports": {"web": [1]}}), encoding="utf-8")
            code, _, err = self._call(["tools", "call", "storage.usage", "--arg", "name=x", "--config", str(path)])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: invalid --config", err)

    def test_a_missing_config_file_is_refused(self):
        code, _, err = self._call(["tools", "call", "storage.usage", "--arg", "name=x", "--config", "no-such-file.json"])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)

    def test_a_payload_that_is_not_utf8_is_invalid_not_a_traceback(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"
            path.write_bytes(b'{"a": "\xff"}')
            code, _, err = self._call(["contracts", "validate", str(path), "--contract", "ToolResult"])
        self.assertEqual(code, 1)
        self.assertIn("INVALID", err)


class EvidenceRedactionTests(unittest.TestCase):
    def test_a_log_line_that_reached_the_bundle_unredacted_is_redacted_there(self):
        result = {
            "requestId": "r1", "status": "ok",
            "output": {"name": "server_log", "lines": ["started", "API_TOKEN=abcd1234secret", "Authorization: Bearer eyJhbGciOi.payload.sig"]},
            "evidence": "read the last 3 line(s) of /var/log/x", "timestamp": "2026-01-01T00:00:00Z",
            "durationMs": 1.0, "toolVersion": "0", "errorCode": None,
        }
        bundle = assemble_evidence_bundle([ObservedResult("logs.read", result)], impact="the service is down")
        joined = "\n".join(bundle["redactedLogExcerpts"])
        self.assertNotIn("abcd1234secret", joined)
        self.assertNotIn("eyJhbGciOi", joined)
        self.assertIn("started", joined)


class OutboxDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.outbox = EscalationOutbox(self.root)

    def test_a_corrupt_entry_is_set_aside_and_the_rest_still_flows(self):
        self.outbox.enqueue("a", {"n": 1})
        (self.root / "pending" / "b.json").write_text("{ half written", encoding="utf-8")
        self.outbox.enqueue("c", {"n": 3})
        sent = []
        self.assertEqual(self.outbox.flush(lambda item: sent.append(item.escalation_id) or True), 2)
        self.assertEqual(sent, ["a", "c"])
        self.assertTrue((self.root / "corrupt" / "b.json").exists(), "the unreadable entry is kept, not deleted")

    def test_an_entry_that_is_not_an_object_is_set_aside(self):
        (self.root / "pending" / "a.json").write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(self.outbox.pending(), [])
        self.assertTrue((self.root / "corrupt" / "a.json").exists())

    def test_a_file_name_the_queue_could_never_mark_sent_is_set_aside(self):
        (self.root / "pending" / "has space.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.outbox.pending(), [])
        self.assertTrue((self.root / "corrupt" / "has space.json").exists())

    def test_a_payload_that_cannot_be_serialised_leaves_nothing_behind(self):
        with self.assertRaises(TypeError):
            self.outbox.enqueue("a", {"bad": object()})
        self.assertEqual(list((self.root / "pending").iterdir()), [])
        self.assertEqual(self.outbox.pending(), [])

    def test_two_corrupt_entries_with_the_same_name_are_both_kept(self):
        for _ in range(2):
            (self.root / "pending" / "a.json").write_text("nope", encoding="utf-8")
            self.outbox.pending()
        self.assertEqual(len(list((self.root / "corrupt").iterdir())), 2)


if __name__ == "__main__":
    unittest.main()
