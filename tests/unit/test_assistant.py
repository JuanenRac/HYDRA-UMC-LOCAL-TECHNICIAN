# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_assistant.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The open assistant: any model behind a chat endpoint, closed by default, advice only. A stand-in endpoint and a real local one."""
import contextlib
import io
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician import assistant, cli
from hydra_umc_local_technician.escalation.evidence import EvidenceAssemblyError, _checksum
from hydra_umc_local_technician.settings import AssistantSettings, SettingsError, parse_settings

ENV_NAME = "HYDRA_UMC_LOCAL_TECHNICIAN_ASSISTANT_KEY"
KEY = "k" * 24
REDACTION_SAMPLE = "password=hunter2hunter2 and Bearer abcdefghijklmnop0123456789"


def make_bundle(**changes):
    bundle = {
        "componentVersions": {"hydra-umc-server": "0.9.1"},
        "relevantManifests": [],
        "redactedLogExcerpts": ["server stopped", REDACTION_SAMPLE],
        "reproductionSteps": ["systemctl is-active hydra-umc-server"],
        "failedTests": ["health"],
        "impact": "The panel shows no robots.",
        "actionsAttempted": [],
        "localValidationResult": "not run",
        "date": "2026-01-01T00:00:00Z",
    }
    bundle.update(changes)
    bundle["checksum"] = _checksum({k: v for k, v in bundle.items() if k != "checksum"})
    return bundle


def settings(**changes):
    values = dict(enabled=True, url="http://127.0.0.1:11434/v1/chat/completions", model="any-model-the-owner-chose")
    values.update(changes)
    return AssistantSettings(**values)


def reply(text="Check the unit.", status=200):
    return lambda url, headers, body, timeout: (status, json.dumps({"choices": [{"message": {"content": text}}]}).encode())


class SettingsTests(unittest.TestCase):
    def test_it_is_closed_and_names_no_model_by_default(self):
        parsed = parse_settings({}).assistant
        self.assertFalse(parsed.enabled)
        self.assertEqual(parsed.model, "")
        self.assertFalse(parsed.allow_remote)
        self.assertFalse(parsed.allow_plain_http)

    def test_enabling_it_needs_an_address_and_the_name_of_a_model(self):
        with self.assertRaisesRegex(SettingsError, "model"):
            parse_settings({"assistant": {"enabled": True, "url": "http://127.0.0.1:1/v1/chat/completions"}})
        with self.assertRaises(SettingsError):
            parse_settings({"assistant": {"enabled": True, "model": "m"}})
        parsed = parse_settings({"assistant": {"enabled": True, "url": "http://127.0.0.1:1/x", "model": "m", "temperature": 0.5, "language": "pt"}}).assistant
        self.assertEqual((parsed.model, parsed.temperature, parsed.language), ("m", 0.5, "pt"))

    def test_unknown_keys_wrong_types_and_ranges_are_errors(self):
        for bad in ({"modell": "x"}, {"enabled": "yes"}, {"allowRemote": 1}, {"timeoutSeconds": 0}, {"maxPromptChars": 10},
                    {"temperature": 3}, {"language": "xx"}, {"apiKeyFile": "relative/key"}, {"maxResponseChars": 1.5}):
            with self.assertRaises(SettingsError, msg=str(bad)):
                parse_settings({"assistant": bad})

    def test_a_config_with_an_assistant_section_passes_the_cli_key_check(self):
        self.assertIn("assistant", cli._CONFIG_KEYS)


class UrlAndKeyTests(unittest.TestCase):
    def test_only_loopback_is_asked_unless_the_owner_opens_it(self):
        assistant.check_url(settings())
        assistant.check_url(settings(url="http://localhost:8080/v1/chat/completions"))
        with self.assertRaisesRegex(assistant.AssistantError, "loopback"):
            assistant.check_url(settings(url="https://models.example.org/v1/chat/completions"))
        assistant.check_url(settings(url="https://models.example.org/v1/chat/completions", allow_remote=True))

    def test_plain_http_to_another_machine_needs_its_own_switch(self):
        with self.assertRaisesRegex(assistant.AssistantError, "plain http"):
            assistant.check_url(settings(url="http://192.168.0.50:8080/x", allow_remote=True))
        assistant.check_url(settings(url="http://192.168.0.50:8080/x", allow_remote=True, allow_plain_http=True))

    def test_bad_schemes_and_credentials_in_the_address_are_refused(self):
        for url in ("ftp://127.0.0.1/x", "http:///x", "http://user:pass@127.0.0.1/x", "file:///etc/passwd"):
            with self.assertRaises(assistant.AssistantError, msg=url):
                assistant.check_url(settings(url=url))

    def test_the_key_comes_from_the_file_or_the_environment_and_may_be_absent(self):
        self.assertEqual(assistant.read_key(settings(), {}), "")
        self.assertEqual(assistant.read_key(settings(), {ENV_NAME: f" {KEY} "}), KEY)
        with self.assertRaisesRegex(assistant.AssistantError, "shorter"):
            assistant.read_key(settings(), {ENV_NAME: "short"})
        with TemporaryDirectory() as directory:
            path = Path(directory) / "key"
            path.write_text(KEY + "\n", encoding="utf-8")
            self.assertEqual(assistant.read_key(settings(api_key_file=str(path)), {ENV_NAME: "ignored" * 4}), KEY)
            with self.assertRaisesRegex(assistant.AssistantError, "key file"):
                assistant.read_key(settings(api_key_file=str(Path(directory) / "missing")), {})


class RequestTests(unittest.TestCase):
    def test_nothing_secret_is_sent_and_the_language_and_model_are_the_settings(self):
        body = assistant.build_request(settings(language="es"), REDACTION_SAMPLE + " and more", "What failed?")
        text = json.dumps(body)
        self.assertNotIn("hunter2hunter2", text)
        self.assertNotIn("abcdefghijklmnop0123456789", text)
        self.assertEqual(body["model"], "any-model-the-owner-chose")
        self.assertIn("Spanish", body["messages"][1]["content"])
        self.assertFalse(body["stream"])
        self.assertEqual(body["temperature"], 0.0)

    def test_a_secret_in_the_question_is_redacted_too(self):
        body = assistant.build_request(settings(), "x", "why does password=hunter2hunter2 fail?")
        self.assertNotIn("hunter2hunter2", json.dumps(body))

    def test_long_material_is_cut_to_the_limit_and_says_so(self):
        body = assistant.build_request(settings(max_prompt_chars=500), "a" * 2000, "q")
        content = body["messages"][1]["content"]
        self.assertIn("[cut:", content)
        self.assertLess(len(content), 900)

    def test_an_empty_question_is_refused(self):
        with self.assertRaises(assistant.AssistantError):
            assistant.build_request(settings(), "x", "   ")

    def test_the_system_prompt_can_come_from_a_file(self):
        self.assertEqual(assistant.system_prompt(settings()), assistant.DEFAULT_SYSTEM_PROMPT)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "prompt.txt"
            path.write_text("Be brief.\n", encoding="utf-8")
            self.assertEqual(assistant.system_prompt(settings(system_prompt_file=str(path))), "Be brief.")
            path.write_text("  \n", encoding="utf-8")
            with self.assertRaisesRegex(assistant.AssistantError, "empty"):
                assistant.system_prompt(settings(system_prompt_file=str(path)))
            with self.assertRaisesRegex(assistant.AssistantError, "prompt file"):
                assistant.system_prompt(settings(system_prompt_file=str(Path(directory) / "none")))

    def test_the_default_prompt_denies_the_assistant_any_authority(self):
        self.assertIn("cannot run anything", assistant.DEFAULT_SYSTEM_PROMPT)


class MaterialTests(unittest.TestCase):
    def test_a_valid_bundle_becomes_text_with_its_evidence(self):
        text = assistant.material_from_bundle(make_bundle())
        self.assertIn("systemctl is-active hydra-umc-server", text)
        self.assertIn("The panel shows no robots.", text)
        self.assertIn("health", text)

    def test_a_bundle_edited_after_assembly_is_refused(self):
        bundle = make_bundle()
        bundle["impact"] = "Nothing is wrong."
        with self.assertRaises(EvidenceAssemblyError):
            assistant.material_from_bundle(bundle)


class AskTests(unittest.TestCase):
    def test_a_closed_assistant_refuses_before_anything_is_sent(self):
        sent = []
        with self.assertRaisesRegex(assistant.AssistantError, "closed"):
            assistant.ask(settings(enabled=False), "x", "q", {}, lambda *a: sent.append(a))
        self.assertEqual(sent, [])

    def test_the_answer_is_advice_and_nothing_else(self):
        answer = assistant.ask(settings(), "evidence", "what now?", {}, reply("Restart is not needed.\x07 Check the log."))
        self.assertTrue(answer.advisory)
        self.assertEqual(answer.model, "any-model-the-owner-chose")
        self.assertEqual(answer.text, "Restart is not needed. Check the log.")
        self.assertFalse(answer.truncated)

    def test_the_answer_is_redacted_and_cut(self):
        answer = assistant.ask(settings(max_response_chars=200), "e", "q", {}, reply("token=abcdef0123456789abcdef " + "x" * 500))
        self.assertNotIn("abcdef0123456789abcdef", answer.text)
        self.assertTrue(answer.truncated)
        self.assertTrue(answer.text.endswith("[cut]"))

    def test_the_key_is_sent_as_a_bearer_header_and_only_when_there_is_one(self):
        seen = []

        def transport(url, headers, body, timeout):
            seen.append((url, dict(headers), body, timeout))
            return reply()(url, headers, body, timeout)

        assistant.ask(settings(), "e", "q", {}, transport)
        assistant.ask(settings(timeout_seconds=7.0), "e", "q", {ENV_NAME: KEY}, transport)
        self.assertNotIn("Authorization", seen[0][1])
        self.assertEqual(seen[1][1]["Authorization"], f"Bearer {KEY}")
        self.assertEqual(seen[1][3], 7.0)
        self.assertNotIn(KEY.encode(), seen[1][2])

    def test_a_bad_status_or_shape_is_an_error_not_an_answer(self):
        with self.assertRaisesRegex(assistant.AssistantError, "status 500"):
            assistant.ask(settings(), "e", "q", {}, reply(status=500))
        for raw in (b"not json", b"{}", b'{"choices": []}', b'{"choices": [{"message": {"content": ""}}]}',
                    b'{"choices": [{"message": {"content": 5}}]}', b'{"choices": [{"message": null}]}'):
            with self.assertRaises(assistant.AssistantError, msg=raw):
                assistant.ask(settings(), "e", "q", {}, lambda *a, raw=raw: (200, raw))

    def test_a_remote_address_is_refused_before_anything_is_sent(self):
        sent = []
        with self.assertRaises(assistant.AssistantError):
            assistant.ask(settings(url="https://models.example.org/v1/chat/completions"), "e", "q", {}, lambda *a: sent.append(a))
        self.assertEqual(sent, [])


class _Endpoint(BaseHTTPRequestHandler):
    received: list = []
    redirect = False

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).received.append((self.headers.get("Authorization", ""), body))
        if type(self).redirect:
            self.send_response(307)
            self.send_header("Location", "http://127.0.0.1:9/elsewhere")
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"choices": [{"message": {"content": "Seen by a real endpoint."}}]}).encode())

    def log_message(self, *args):
        pass


class RealEndpointTests(unittest.TestCase):
    def setUp(self):
        _Endpoint.received = []
        _Endpoint.redirect = False
        self.server = HTTPServer(("127.0.0.1", 0), _Endpoint)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1/chat/completions"

    def tearDown(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()

    def test_a_question_goes_to_a_real_local_endpoint(self):
        answer = assistant.ask(settings(url=self.url), "evidence", "what failed?", {ENV_NAME: KEY})
        self.assertEqual(answer.text, "Seen by a real endpoint.")
        header, body = _Endpoint.received[0]
        self.assertEqual(header, f"Bearer {KEY}")
        self.assertEqual(body["model"], "any-model-the-owner-chose")

    def test_a_redirect_is_not_followed(self):
        _Endpoint.redirect = True
        with self.assertRaises(assistant.AssistantError):
            assistant.ask(settings(url=self.url), "evidence", "q", {})
        self.assertEqual(len(_Endpoint.received), 1)

    def test_a_closed_port_is_an_error(self):
        self.server.shutdown()
        self.server.server_close()
        with self.assertRaisesRegex(assistant.AssistantError, "did not answer"):
            assistant.ask(settings(url=self.url, timeout_seconds=2), "e", "q", {})
        self.server = None


class CommandTests(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_the_command_is_refused_while_the_assistant_is_closed(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text("{}", encoding="utf-8")
            text = Path(directory) / "text.txt"
            text.write_text("log", encoding="utf-8")
            code, out, err = self.run_cli("assistant", "ask", "--config", str(config), "--text", str(text), "--question", "q")
        self.assertEqual(code, 2)
        self.assertIn("closed", err)
        self.assertEqual(out, "")

    def test_the_command_prints_advice_marked_as_such(self):
        server = HTTPServer(("127.0.0.1", 0), _Endpoint)
        _Endpoint.received = []
        _Endpoint.redirect = False
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with TemporaryDirectory() as directory:
                config = Path(directory) / "config.json"
                url = f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"
                config.write_text(json.dumps({"assistant": {"enabled": True, "url": url, "model": "m"}}), encoding="utf-8")
                bundle = Path(directory) / "bundle.json"
                bundle.write_text(json.dumps(make_bundle()), encoding="utf-8")
                output = Path(directory) / "advice.txt"
                code, out, err = self.run_cli("assistant", "ask", "--config", str(config), "--bundle", str(bundle), "--question", "q")
                code_file, out_file, _ = self.run_cli(
                    "assistant", "ask", "--config", str(config), "--bundle", str(bundle), "--question", "q", "--output", str(output))
                saved = output.read_text(encoding="utf-8")
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual((code, err), (0, ""))
        self.assertIn("ADVISORY", out)
        self.assertIn("nothing was run", out)
        self.assertIn("Seen by a real endpoint.", out)
        self.assertEqual(code_file, 0)
        self.assertIn("ADVICE ->", out_file)
        self.assertIn("ADVISORY", saved)
        sent = json.dumps(_Endpoint.received[0][1])
        self.assertNotIn("hunter2hunter2", sent)

    def test_a_changed_bundle_is_refused_by_the_command(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text(json.dumps({"assistant": {"enabled": True, "url": "http://127.0.0.1:9/x", "model": "m"}}), encoding="utf-8")
            bundle = make_bundle()
            bundle["impact"] = "edited"
            path = Path(directory) / "bundle.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            code, out, err = self.run_cli("assistant", "ask", "--config", str(config), "--bundle", str(path), "--question", "q")
        self.assertEqual(code, 2)
        self.assertIn("checksum", err)


if __name__ == "__main__":
    unittest.main()
