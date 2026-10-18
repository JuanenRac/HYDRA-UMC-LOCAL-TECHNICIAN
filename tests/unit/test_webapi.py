# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_webapi.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The read-only local API and its web page: every endpoint, GET only, no way
to reach a file outside the stores, the same redaction as the CLI, bounded
answers, the token rule and the page's offline / eight-language guarantees."""
import contextlib
import http.client
import io
import json
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from hydra_umc_local_technician import webapi
from hydra_umc_local_technician.cli import main
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.webapi import (
    LANGUAGES,
    MAX_DOC_CHARS,
    MAX_ITEM_BYTES,
    MAX_LIST_ITEMS,
    ApiConfigError,
    TechnicianServer,
    validate_bind,
)

TOKEN = "t" * 32
SECRET_BITS = ("hunter2-token-value", "swordfish99", "abcdef0123456789", "dXNlcjpwYXNzd29yZA")
WEBUI = Path(webapi.__file__).resolve().parent / "webui"


def _tool_result(request_id="r1", evidence="read /opt/x"):
    return {
        "requestId": request_id, "status": "ok", "output": {"found": True}, "evidence": evidence,
        "timestamp": "2026-01-01T00:00:00+00:00", "durationMs": 1.5, "toolVersion": "0.0.0", "errorCode": None,
    }


class ServerCase(unittest.TestCase):
    token: str | None = None
    host = "127.0.0.1"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.data = self.root / "data"
        for name in ("tool-results", "evidence", "proposals"):
            (self.data / name).mkdir(parents=True)
        self.eco = self.root / "eco"
        project = self.eco / "HYDRA-UMC-DEMO"
        project.mkdir(parents=True)
        (project / "hydra-umc.project.json").write_text(
            json.dumps({"name": "HYDRA-UMC-DEMO", "version": "1.2.3", "maturity": "functional", "role": "service"}), encoding="utf-8"
        )
        (self.eco / "not-a-project").mkdir()
        self.docs = self.root / "docs"
        self.docs.mkdir()
        (self.docs / "guide.md").write_text("# Guide\nUse the tool.\npassword=swordfish99\n", encoding="utf-8")
        (self.docs / "sub").mkdir()
        (self.docs / "sub" / "contract.json").write_text('{"a": 1}', encoding="utf-8")
        (self.root / "outside.json").write_text('{"secret": "outside"}', encoding="utf-8")
        (self.root / "outside.md").write_text("# Out\nnot in the index\n", encoding="utf-8")
        config = OrchestratorConfig(ecosystem_root=self.eco, knowledge_sources={"docs": self.docs})
        self.server = TechnicianServer((self.host, 0), data_dir=self.data, config=config, token=self.token)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self._stop)

    def _stop(self):
        self.server.shutdown()
        self.server.server_close()

    def put(self, store, name, value):
        text = value if isinstance(value, str) else json.dumps(value)
        (self.data / store / f"{name}.json").write_text(text, encoding="utf-8")

    def call(self, method, path, token=None, headers=None, body=None, host_header=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            all_headers = dict(headers or {})
            if token:
                all_headers["Authorization"] = f"Bearer {token}"
            if host_header is not None:
                connection.putrequest(method, path, skip_host=True)
                connection.putheader("Host", host_header)
                for name, value in all_headers.items():
                    connection.putheader(name, value)
                connection.endheaders()
            else:
                connection.request(method, path, body=body, headers=all_headers)
            response = connection.getresponse()
            raw = response.read()
            return response.status, dict(response.getheaders()), raw
        finally:
            connection.close()

    def get_json(self, path, token=None):
        status, headers, raw = self.call("GET", path, token=token)
        return status, json.loads(raw) if raw else None


class EndpointTests(ServerCase):
    def test_health_and_tools(self):
        status, body = self.get_json("/api/v1/health")
        self.assertEqual((status, body["status"], body["readOnly"]), (200, "ok", True))
        status, body = self.get_json("/api/v1/tools")
        names = {tool["name"] for tool in body["tools"]}
        self.assertEqual(status, 200)
        self.assertIn("service.status", names)
        self.assertIn("knowledge.search", names)

    def test_each_store_lists_and_shows_its_items(self):
        self.put("tool-results", "r1", _tool_result())
        self.put("evidence", "e1", {"date": "d", "impact": "slow", "checksum": "c"})
        self.put("proposals", "p1", {"risk": "prepare", "scope": "unit", "diagnosis": "dead"})
        for store, item_id in (("tool-results", "r1"), ("evidence", "e1"), ("proposals", "p1")):
            status, listing = self.get_json(f"/api/v1/{store}")
            self.assertEqual(status, 200, store)
            self.assertEqual([i["id"] for i in listing["items"]], [item_id])
            self.assertEqual(listing["total"], 1)
            status, detail = self.get_json(f"/api/v1/{store}/{item_id}")
            self.assertEqual((status, detail["id"]), (200, item_id))
        self.assertEqual(self.get_json("/api/v1/tool-results")[1]["items"][0]["status"], "ok")
        self.assertEqual(self.get_json("/api/v1/proposals")[1]["items"][0]["risk"], "prepare")
        self.assertEqual(self.get_json("/api/v1/evidence/e1")[1]["item"]["impact"], "slow")

    def test_missing_stores_and_items(self):
        self.assertEqual(self.get_json("/api/v1/tool-results/nope")[0], 404)
        (self.data / "evidence").rmdir()
        status, listing = self.get_json("/api/v1/evidence")
        self.assertEqual((status, listing["items"], listing["total"]), (200, [], 0))

    def test_invalid_json_is_listed_with_a_problem_and_refused_in_detail(self):
        self.put("evidence", "broken", "{not json")
        self.put("evidence", "list", "[1, 2]")
        status, listing = self.get_json("/api/v1/evidence")
        by_id = {i["id"]: i for i in listing["items"]}
        self.assertEqual(by_id["broken"]["problem"], "unreadable")
        self.assertNotIn("problem", by_id["list"])
        self.assertEqual(self.get_json("/api/v1/evidence/broken")[0], 422)

    def test_non_json_files_are_ignored(self):
        (self.data / "evidence" / "notes.txt").write_text("x", encoding="utf-8")
        (self.data / "evidence" / "sub").mkdir()
        self.assertEqual(self.get_json("/api/v1/evidence")[1]["total"], 0)

    def test_manifests_list_and_detail(self):
        status, body = self.get_json("/api/v1/manifests")
        self.assertEqual(status, 200)
        self.assertTrue(body["configured"])
        self.assertEqual([p["project"] for p in body["projects"]], ["HYDRA-UMC-DEMO"])
        self.assertEqual(body["projects"][0]["version"], "1.2.3")
        status, one = self.get_json("/api/v1/manifests/HYDRA-UMC-DEMO")
        self.assertEqual((status, one["maturity"]), (200, "functional"))
        self.assertEqual(self.get_json("/api/v1/manifests/not-a-project")[0], 404)
        self.assertEqual(self.get_json("/api/v1/manifests/HYDRA-UMC-DEMO/extra")[0], 404)

    def test_manifests_without_an_ecosystem_root(self):
        self.server.config = OrchestratorConfig()
        self.assertEqual(self.get_json("/api/v1/manifests"), (200, {"configured": False, "projects": []}))

    def test_docs_index_and_document(self):
        status, body = self.get_json("/api/v1/docs")
        self.assertEqual(status, 200)
        source = body["sources"][0]
        self.assertEqual(source["name"], "docs")
        self.assertEqual(sorted(source["documents"]), ["guide.md", "sub/contract.json"])
        status, doc = self.get_json("/api/v1/docs/docs?path=guide.md")
        self.assertEqual(status, 200)
        self.assertIn("Use the tool.", doc["chunks"][0]["text"])
        status, doc = self.get_json("/api/v1/docs/docs?path=sub%2Fcontract.json")
        self.assertEqual((status, doc["chunks"][0]["kind"]), (200, "json"))
        self.assertEqual(self.get_json("/api/v1/docs/ghost?path=guide.md")[0], 404)
        self.assertEqual(self.get_json("/api/v1/docs/docs")[0], 404)

    def test_unknown_routes_are_404(self):
        for path in ("/api/v1/", "/api/v1/nothing", "/api/v1/tools/extra", "/elsewhere", "/api/v2/tools"):
            self.assertEqual(self.call("GET", path)[0], 404, path)


class ReadOnlyTests(ServerCase):
    def test_every_other_method_is_refused_and_nothing_is_written(self):
        self.put("evidence", "e1", {"impact": "x"})
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        contents = (self.data / "evidence" / "e1.json").read_text(encoding="utf-8")
        for method in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD", "TRACE"):
            for path in ("/api/v1/evidence", "/api/v1/evidence/e1", "/api/v1/tools", "/", "/app.js", "/nope"):
                status, headers, _ = self.call(method, path, body=b"{}" if method in ("POST", "PUT", "PATCH") else None)
                self.assertEqual(status, 405, f"{method} {path}")
                self.assertEqual(headers.get("Allow"), "GET")
        self.assertEqual(sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")), before)
        self.assertEqual((self.data / "evidence" / "e1.json").read_text(encoding="utf-8"), contents)

    def test_a_body_sent_to_a_get_is_never_read(self):
        status, _, _ = self.call("GET", "/api/v1/tools", body=b"x" * 100_000, headers={"Content-Type": "application/json"})
        self.assertEqual(status, 200)

    def test_the_module_opens_nothing_for_writing(self):
        source = Path(webapi.__file__).read_text(encoding="utf-8")
        for forbidden in ("write_text", "write_bytes", ".mkdir(", "unlink", "os.remove", "rename(", "shutil", "subprocess"):
            self.assertNotIn(forbidden, source, forbidden)
        self.assertNotRegex(source, r"open\([^)]*[\"'][wax+]")


class PathTraversalTests(ServerCase):
    def test_an_id_that_is_not_a_listed_file_never_reaches_the_disk(self):
        self.put("evidence", "e1", {"impact": "x"})
        (self.data / "secret.json").write_text('{"secret": "data-dir"}', encoding="utf-8")
        attempts = [
            "/api/v1/evidence/..%2fsecret",
            "/api/v1/evidence/..%2f..%2foutside",
            "/api/v1/evidence/%2e%2e%2foutside",
            "/api/v1/evidence/../secret",
            "/api/v1/evidence/..\\secret",
            "/api/v1/evidence/..%5csecret",
            "/api/v1/evidence/%2fetc%2fpasswd",
            "/api/v1/evidence/C:%5cWindows%5cwin.ini",
            "/api/v1/evidence/e1%00.json",
            "/api/v1/evidence/e1.json",
            "/api/v1/evidence/e1/",
            "/api/v1/tool-results/..",
            "/api/v1/tool-results/.",
        ]
        for path in attempts:
            status, _, raw = self.call("GET", path)
            self.assertIn(status, (404, 301), path)
            self.assertNotIn(b"outside", raw, path)
            self.assertNotIn(b"data-dir", raw, path)

    def test_a_link_pointing_outside_the_store_is_not_served(self):
        link = self.data / "evidence" / "linked.json"
        try:
            os.symlink(self.root / "outside.json", link)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are not available here")
        self.assertEqual(self.get_json("/api/v1/evidence/linked")[0], 404)
        self.assertEqual(self.get_json("/api/v1/evidence")[1]["total"], 0)

    def test_documents_outside_the_index_cannot_be_asked_for(self):
        for wanted in (
            "../outside.md", "..%2foutside.md", "%2e%2e%2foutside.md", "../../outside.json",
            "/etc/passwd", "C:%5cWindows%5cwin.ini", "guide.md%00", "sub/../../outside.md", "", "GUIDE.MD",
        ):
            status, _, raw = self.call("GET", f"/api/v1/docs/docs?path={wanted}")
            self.assertEqual(status, 404, wanted)
            self.assertNotIn(b"not in the index", raw)

    def test_manifest_names_cannot_leave_the_ecosystem_root(self):
        for name in ("..", "..%2foutside", "HYDRA-UMC-..%2f..", "%2e%2e", "HYDRA-UMC-DEMO%2f..%2f..%2foutside"):
            self.assertEqual(self.call("GET", f"/api/v1/manifests/{name}")[0], 404, name)


class BoundsTests(ServerCase):
    def test_an_item_over_the_limit_is_refused(self):
        self.put("evidence", "big", json.dumps({"impact": "x" * (MAX_ITEM_BYTES + 10)}))
        status, body = self.get_json("/api/v1/evidence/big")
        self.assertEqual(status, 413)
        self.assertIn("error", body)
        listing = self.get_json("/api/v1/evidence")[1]
        self.assertEqual(listing["items"][0]["problem"], "too_large")

    def test_an_item_just_under_the_limit_is_served_whole(self):
        padding = "x" * (MAX_ITEM_BYTES - 200)
        self.put("evidence", "edge", {"impact": padding})
        status, headers, raw = self.call("GET", "/api/v1/evidence/edge")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(raw)["item"]["impact"]), len(padding))
        self.assertEqual(int(headers["Content-Length"]), len(raw))

    def test_lists_are_paged_and_capped(self):
        for number in range(MAX_LIST_ITEMS + 25):
            self.put("tool-results", f"r{number:04d}", {"status": "ok"})
        status, first = self.get_json("/api/v1/tool-results")
        self.assertEqual((len(first["items"]), first["total"]), (100, MAX_LIST_ITEMS + 25))
        status, huge = self.get_json("/api/v1/tool-results?limit=1000000")
        self.assertEqual(len(huge["items"]), MAX_LIST_ITEMS)
        status, tail = self.get_json(f"/api/v1/tool-results?offset={MAX_LIST_ITEMS}&limit=500")
        self.assertEqual(len(tail["items"]), 25)
        for query in ("limit=abc", "offset=-5", "limit=-1", "offset=zzz"):
            self.assertEqual(self.call("GET", f"/api/v1/tool-results?{query}")[0], 200, query)

    def test_a_large_document_is_cut_and_says_so(self):
        (self.docs / "huge.md").write_text("# Huge\n" + ("lorem ipsum dolor sit amet\n" * 20_000), encoding="utf-8")
        status, doc = self.get_json("/api/v1/docs/docs?path=huge.md")
        self.assertEqual(status, 200)
        self.assertTrue(doc["truncated"])
        self.assertLessEqual(sum(len(c["text"]) for c in doc["chunks"]), MAX_DOC_CHARS)

    def test_a_request_with_an_oversized_header_does_not_break_the_server(self):
        status, _, _ = self.call("GET", "/api/v1/tools", headers={"X-Pad": "a" * 70_000})
        self.assertIn(status, (400, 431, 414))
        self.assertEqual(self.get_json("/api/v1/health")[0], 200)

    def test_a_very_long_path_is_refused_not_served(self):
        status, _, _ = self.call("GET", "/api/v1/evidence/" + "a" * 70_000)
        self.assertIn(status, (404, 414))
        self.assertEqual(self.get_json("/api/v1/health")[0], 200)


class RedactionTests(ServerCase):
    def test_nothing_secret_leaves_in_any_answer(self):
        self.put("tool-results", "r1", _tool_result(evidence="ran streamer --token hunter2-token-value --port 8080"))
        self.put("evidence", "e1", {
            "impact": "Cookie: session=abcdef0123456789", "password": "swordfish99",
            "relevantManifests": ["Authorization: Basic dXNlcjpwYXNzd29yZA=="],
        })
        self.put("proposals", "p1", {"diagnosis": "api_key=swordfish99", "steps": ["--token hunter2-token-value"]})
        paths = [
            "/api/v1/tool-results", "/api/v1/tool-results/r1", "/api/v1/evidence", "/api/v1/evidence/e1",
            "/api/v1/proposals", "/api/v1/proposals/p1", "/api/v1/docs/docs?path=guide.md",
        ]
        for path in paths:
            status, _, raw = self.call("GET", path)
            self.assertEqual(status, 200, path)
            text = raw.decode("utf-8")
            for bit in SECRET_BITS:
                self.assertNotIn(bit, text, f"{path} leaks {bit}")
        self.assertIn("[REDACTED]", self.call("GET", "/api/v1/tool-results/r1")[2].decode("utf-8"))
        self.assertIn("--port 8080", self.call("GET", "/api/v1/tool-results/r1")[2].decode("utf-8"))

    def test_the_answer_matches_what_the_cli_redaction_does(self):
        from hydra_umc_local_technician.knowledge.redaction import redact_json
        stored = _tool_result(evidence="--token hunter2-token-value")
        self.put("tool-results", "r1", stored)
        self.assertEqual(self.get_json("/api/v1/tool-results/r1")[1]["item"], redact_json(stored))


class TokenAndHostTests(ServerCase):
    token = TOKEN

    def test_data_routes_need_the_token_but_the_page_and_health_do_not(self):
        self.assertEqual(self.call("GET", "/")[0], 200)
        self.assertEqual(self.call("GET", "/app.js")[0], 200)
        self.assertEqual(self.call("GET", "/api/v1/health")[0], 200)
        for path in ("/api/v1/tools", "/api/v1/evidence", "/api/v1/manifests", "/api/v1/docs"):
            self.assertEqual(self.call("GET", path)[0], 401, path)
            self.assertEqual(self.call("GET", path, token="x" * 32)[0], 401, path)
            self.assertEqual(self.call("GET", path, token=TOKEN[:-1])[0], 401, path)
            self.assertEqual(self.call("GET", path, token=TOKEN)[0], 200, path)
        status, headers, _ = self.call("GET", "/api/v1/tools")
        self.assertEqual(headers.get("WWW-Authenticate"), "Bearer")

    def test_other_authorization_schemes_are_refused(self):
        self.assertEqual(self.call("GET", "/api/v1/tools", headers={"Authorization": f"Basic {TOKEN}"})[0], 401)
        self.assertEqual(self.call("GET", "/api/v1/tools", headers={"Authorization": TOKEN})[0], 401)


class HostHeaderTests(ServerCase):
    def test_a_foreign_host_name_is_refused_on_a_loopback_bind(self):
        for host in ("evil.example.com", "evil.example.com:8780", "127.0.0.1.evil.com", "10.0.0.5"):
            self.assertEqual(self.call("GET", "/api/v1/tools", host_header=host)[0], 403, host)
            self.assertEqual(self.call("GET", "/", host_header=host)[0], 403, host)
        for host in ("127.0.0.1", f"127.0.0.1:{self.port}", "localhost", f"localhost:{self.port}", f"[::1]:{self.port}"):
            self.assertEqual(self.call("GET", "/api/v1/tools", host_header=host)[0], 200, host)


class NonLoopbackBindTests(unittest.TestCase):
    def test_the_bind_rules(self):
        validate_bind("127.0.0.1", None)
        validate_bind("::1", None)
        validate_bind("localhost", None)
        validate_bind("127.0.0.1", TOKEN)
        validate_bind("0.0.0.0", TOKEN)
        validate_bind("192.168.1.20", TOKEN)
        for host in ("0.0.0.0", "192.168.1.20", "::", "example.org"):
            with self.assertRaises(ApiConfigError, msg=host):
                validate_bind(host, None)
            with self.assertRaises(ApiConfigError, msg=host):
                validate_bind(host, "")
            with self.assertRaises(ApiConfigError, msg=host):
                validate_bind(host, "short")
        with self.assertRaises(ApiConfigError):
            validate_bind("127.0.0.1", "short")

    def test_the_server_refuses_to_start_without_a_token_off_loopback(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ApiConfigError):
                TechnicianServer(("0.0.0.0", 0), data_dir=Path(tmp), config=OrchestratorConfig(), token=None)

    def test_off_loopback_with_a_token_serves_and_enforces_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = TechnicianServer(("0.0.0.0", 0), data_dir=Path(tmp), config=OrchestratorConfig(), token=TOKEN)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                port = server.server_address[1]
                for token, expected in ((None, 401), ("x" * 32, 401), (TOKEN, 200)):
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    connection.request("GET", "/api/v1/tools", headers=headers)
                    self.assertEqual(connection.getresponse().status, expected, token)
                    connection.close()
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                connection.request("POST", "/api/v1/tools", headers={"Authorization": f"Bearer {TOKEN}"})
                self.assertEqual(connection.getresponse().status, 405)
                connection.close()
            finally:
                server.shutdown()
                server.server_close()

    def test_the_cli_refuses_an_open_bind_and_a_short_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with contextlib.redirect_stderr(err), mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("HYDRA_UMC_LOCAL_TECHNICIAN_TOKEN", None)
                self.assertEqual(main(["serve", "--host", "0.0.0.0", "--data-dir", tmp]), 1)
            self.assertIn("REFUSED", err.getvalue())
            token_file = Path(tmp) / "token"
            token_file.write_text("short", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["serve", "--data-dir", tmp, "--token-file", str(token_file)]), 1)
                self.assertEqual(main(["serve", "--data-dir", tmp, "--port", "70000"]), 1)
                self.assertEqual(main(["serve", "--data-dir", tmp, "--config", str(Path(tmp) / "missing.json")]), 1)

    def test_the_cli_serves_on_loopback_and_stops_on_interrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out), mock.patch.object(TechnicianServer, "serve_forever", side_effect=KeyboardInterrupt):
                self.assertEqual(main(["serve", "--data-dir", tmp, "--port", "0"]), 0)
            self.assertIn("GET only", out.getvalue())
            self.assertIn("127.0.0.1", out.getvalue())

    def test_the_token_is_never_taken_from_the_command_line(self):
        from hydra_umc_local_technician.cli import build_parser
        parser = build_parser()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["serve", "--data-dir", ".", "--token", "x" * 32])


class StaticPageTests(ServerCase):
    def test_the_page_and_its_assets_are_served_with_a_strict_policy(self):
        for path, kind in (("/", "text/html"), ("/index.html", "text/html"), ("/app.js", "text/javascript"), ("/app.css", "text/css")):
            status, headers, raw = self.call("GET", path)
            self.assertEqual(status, 200, path)
            self.assertTrue(headers["Content-Type"].startswith(kind), path)
            self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
            self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertGreater(len(raw), 100)

    def test_only_the_known_static_files_exist(self):
        for path in ("/webui/app.js", "/i18n/xx.json", "/i18n/../app.js", "/i18n/en.json.bak", "/app.js.map", "/../webapi.py", "/%2e%2e/webapi.py"):
            self.assertEqual(self.call("GET", path)[0], 404, path)

    def test_nothing_is_loaded_from_outside(self):
        for name in ("index.html", "app.js", "app.css"):
            text = (WEBUI / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)(https?:)?//[a-z0-9.-]+\.[a-z]{2,}", name)
            self.assertNotRegex(text, r"(?i)@import|<link[^>]+href=[\"']https?", name)
            self.assertNotIn("innerHTML", text, name)
            self.assertNotIn("eval(", text, name)
        html = (WEBUI / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r"(?is)<script(?![^>]*\bsrc=)[^>]*>")  # no inline script
        self.assertNotRegex(html, r"(?i)\sstyle=")
        self.assertNotRegex((WEBUI / "app.js").read_text(encoding="utf-8"), r"method:\s*[\"'](?!GET)")

    def test_the_page_is_accessible_and_responsive(self):
        html = (WEBUI / "index.html").read_text(encoding="utf-8")
        for needle in ('<html lang="en">', 'name="viewport"', 'class="skip"', 'role="status"', 'aria-live="polite"', '<main id="main"', '<label for="lang"', '<label for="token"', "aria-labelledby"):
            self.assertIn(needle, html)
        css = (WEBUI / "app.css").read_text(encoding="utf-8")
        for needle in (":focus-visible", "@media (max-width", "prefers-color-scheme", "prefers-reduced-motion"):
            self.assertIn(needle, css)


class EightLanguagesTests(unittest.TestCase):
    def _locales(self):
        return {code: json.loads((WEBUI / "i18n" / f"{code}.json").read_text(encoding="utf-8")) for code in LANGUAGES}

    def test_the_eight_languages_are_exactly_these(self):
        self.assertEqual(LANGUAGES, ("en", "es", "de", "fr", "it", "ja", "zh", "pt"))
        self.assertEqual(sorted(p.stem for p in (WEBUI / "i18n").glob("*.json")), sorted(LANGUAGES))
        html = (WEBUI / "index.html").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'<option value="([a-z]{2})"', html), list(LANGUAGES))
        self.assertIn("Português (Portugal)", html)

    def test_every_language_has_every_string(self):
        locales = self._locales()
        reference = set(locales["en"])
        for code, strings in locales.items():
            self.assertEqual(set(strings), reference, code)
            for key, value in strings.items():
                self.assertTrue(isinstance(value, str) and value.strip(), f"{code}.{key}")
        for code, strings in locales.items():
            self.assertIn("{shown}", strings["count"], code)
            self.assertIn("{total}", strings["count"], code)
        for code in LANGUAGES:
            if code != "en":
                differing = sum(1 for k, v in locales[code].items() if v != locales["en"][k])
                self.assertGreater(differing, len(reference) - 4, code)  # translated, not copied

    def test_every_string_the_page_asks_for_exists(self):
        reference = set(self._locales()["en"])
        html = (WEBUI / "index.html").read_text(encoding="utf-8")
        js = (WEBUI / "app.js").read_text(encoding="utf-8")
        used = set(re.findall(r'data-i18n(?:-placeholder)?="([a-z_-]+)"', html))
        used |= set(re.findall(r'\bt\("([a-z_-]+)"', js))
        used |= {f"nav_{name}" for name in re.findall(r'"(tools|tool-results|evidence|proposals|manifests|docs)"', js.split("var ORDER", 1)[1].split("]", 1)[0])}
        for key in re.findall(r'"(err_[a-z_]+)"', js):
            used.add(key)
        used |= set(re.findall(r'"(implemented_(?:yes|no))"', js))
        used.discard("nav_")  # the prefix of the per-section keys built above
        self.assertLessEqual(used, reference, sorted(used - reference))
        self.assertTrue({"title", "nav_tools", "count", "err_auth"} <= used)

    def test_portuguese_is_the_european_variant(self):
        pt = self._locales()["pt"]
        self.assertEqual(pt["loading"], "A carregar…")
        self.assertEqual(pt["nav_label"], "Secções")
        self.assertNotIn("Carregando", json.dumps(pt, ensure_ascii=False))
        self.assertIn('"pt-PT"', (WEBUI / "app.js").read_text(encoding="utf-8"))

    def test_each_language_file_is_served(self):
        class Probe(ServerCase):
            def runTest(self):  # pragma: no cover - driven below
                pass
        probe = Probe()
        probe.setUp()
        try:
            for code in LANGUAGES:
                status, headers, raw = probe.call("GET", f"/i18n/{code}.json")
                self.assertEqual(status, 200, code)
                self.assertEqual(json.loads(raw), self._locales()[code])
        finally:
            probe.doCleanups()


if __name__ == "__main__":
    unittest.main()
