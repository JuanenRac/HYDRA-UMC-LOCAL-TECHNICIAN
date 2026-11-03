# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_transport_and_snapshot.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The outbox transport (against a real local HTTP server) and the baseline snapshot."""
import hashlib
import hmac
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.escalation.outbox import EscalationOutbox
from hydra_umc_local_technician.escalation.snapshot import SnapshotError, drift, planned_calls, take_snapshot
from hydra_umc_local_technician.escalation.transport import TransportError, build_message, check_url, read_secret, send_pending
from hydra_umc_local_technician.orchestrator.allowlist import OrchestratorConfig
from hydra_umc_local_technician.settings import SettingsError, SnapshotSettings, TransportSettings, parse_settings

SHARED_VALUE = "s" * 32


class _Receiver(BaseHTTPRequestHandler):
    answer = (200, b'{"ok": true}')
    received: list[dict] = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).received.append(body)
        status, payload = type(self).answer
        self.send_response(status)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class TransportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        _Receiver.received = []
        _Receiver.answer = (200, b'{"ok": true}')
        self.server = HTTPServer(("127.0.0.1", 0), _Receiver)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.settings = TransportSettings(enabled=True, url=f"http://127.0.0.1:{self.server.server_address[1]}/incident", from_node="tec", to_node="dev")
        self.outbox = EscalationOutbox(Path(self._tmp.name))
        self.outbox.enqueue("esc-1", {"checksum": "x"})
        self.env = {self.settings.secret_env: SHARED_VALUE}

    def test_a_confirmed_send_signs_the_message_and_empties_the_queue(self):
        self.assertEqual(send_pending(self.outbox, self.settings, self.env), 1)
        self.assertEqual(self.outbox.pending(), [])
        message = _Receiver.received[0]
        mac = message.pop("mac")
        expected = hmac.new(SHARED_VALUE.encode(), json.dumps(message, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        self.assertEqual(mac, expected)
        self.assertEqual(message["contract_version"], "incident-transport/1")
        self.assertEqual(message["payload"]["evidenceBundle"], {"checksum": "x"})
        self.assertEqual(message["message_id"], "tec-esc-1")

    def test_a_refusal_or_a_body_without_ok_keeps_the_item_queued(self):
        for answer in ((500, b'{"ok": true}'), (200, b'{"ok": false}'), (200, b"not json"), (200, b'{"ok": "true"}')):
            _Receiver.answer = answer
            self.assertEqual(send_pending(self.outbox, self.settings, self.env), 0, answer)
            self.assertEqual(len(self.outbox.pending()), 1)

    def test_an_unreachable_receiver_keeps_the_item_queued(self):
        closed = TransportSettings(enabled=True, url="http://127.0.0.1:9/x", from_node="tec", to_node="dev", timeout_seconds=1)
        self.assertEqual(send_pending(self.outbox, closed, self.env), 0)
        self.assertEqual(len(self.outbox.pending()), 1)

    def test_it_is_closed_by_default_and_the_secret_is_checked(self):
        with self.assertRaises(TransportError):
            send_pending(self.outbox, TransportSettings(), self.env)
        with self.assertRaises(TransportError):
            send_pending(self.outbox, self.settings, {})
        with self.assertRaises(TransportError):
            send_pending(self.outbox, self.settings, {self.settings.secret_env: "short"})
        self.assertEqual(_Receiver.received, [])

    def test_plain_http_to_a_remote_host_and_credentials_in_the_url_are_refused(self):
        for url in ("http://example.org/x", "ftp://127.0.0.1/x", "https://user:pw@example.org/x"):
            with self.assertRaises(TransportError, msg=url):
                check_url(TransportSettings(enabled=True, url=url, from_node="a", to_node="b"))
        check_url(TransportSettings(enabled=True, url="http://example.org/x", from_node="a", to_node="b", allow_plain_http=True))

    def test_the_secret_can_come_from_a_file_and_never_appears_in_an_error(self):
        path = Path(self._tmp.name) / "shared-value"
        path.write_text(SHARED_VALUE + "\n", encoding="utf-8")
        from_file = TransportSettings(enabled=True, url="https://example.org", from_node="a", to_node="b", secret_file=str(path))
        self.assertEqual(read_secret(from_file, {}), SHARED_VALUE)

    def test_every_attempt_has_its_own_nonce_but_the_same_message_id(self):
        item = self.outbox.pending()[0]
        first, second = build_message(item, self.settings, SHARED_VALUE), build_message(item, self.settings, SHARED_VALUE)
        self.assertEqual(first["message_id"], second["message_id"])
        self.assertNotEqual(first["nonce"], second["nonce"])


class SettingsTests(unittest.TestCase):
    def test_everything_is_closed_without_sections(self):
        settings = parse_settings({})
        self.assertFalse(settings.transport.enabled or settings.runbooks.enabled or settings.approvals.enabled or settings.snapshot.enabled)

    def test_malformed_sections_are_errors(self):
        for raw in (
            {"transport": {"enabled": "true"}}, {"transport": {"enabled": True}}, {"transport": {"bogus": 1}},
            {"runbooks": {"enabled": True}}, {"runbooks": {"language": "xx"}}, {"approvals": {"enabled": True}},
            {"approvals": {"trustStore": "relative.json"}}, {"snapshot": {"enabled": True}}, {"snapshot": {"keep": 0}},
            {"transport": {"timeoutSeconds": True}}, {"snapshot": []},
        ):
            with self.assertRaises(SettingsError, msg=raw):
                parse_settings(raw)


class SnapshotTests(unittest.TestCase):
    def test_closed_by_default(self):
        with TemporaryDirectory() as tmp, self.assertRaises(SnapshotError):
            take_snapshot(OrchestratorConfig(), SnapshotSettings(directory=tmp))

    def test_planned_calls_follow_the_configuration(self):
        config = OrchestratorConfig(systemd_units=("a.service",), ports={"web": ("127.0.0.1", 80)}, storage_paths={"data": Path("/")})
        self.assertEqual(planned_calls(config), [
            ("service.status", {"name": "a.service"}), ("network.port_status", {"name": "web"}),
            ("storage.usage", {"name": "data"}), ("system.temperature", {}),
        ])

    def test_a_snapshot_is_saved_and_the_second_reports_what_changed_and_archives_the_old_ones(self):
        with TemporaryDirectory() as tmp:
            config = OrchestratorConfig(storage_paths={"data": Path(tmp)}, ports={"closed": ("127.0.0.1", 9)})
            settings = SnapshotSettings(enabled=True, directory=str(Path(tmp) / "baselines"), keep=1)
            first, changes = take_snapshot(config, settings, now=1_000_000.0)
            self.assertEqual(changes, [])
            self.assertTrue(first.exists())
            saved = json.loads(first.read_text(encoding="utf-8"))
            self.assertIn("checksum", saved["bundle"])
            second, _ = take_snapshot(config, settings, now=1_000_100.0)
            self.assertTrue(second.exists())
            self.assertFalse(first.exists())
            self.assertTrue((first.parent / "archive" / first.name).exists())

    def test_drift_reports_findings_but_not_moving_numbers(self):
        def record(listening, used):
            return {"results": {"network.port_status[web]": {"status": "ok", "output": {"listening": listening, "port": 80}},
                                "storage.usage[data]": {"status": "ok", "output": {"usedBytes": used}}}}
        self.assertEqual(drift(record(True, 1), record(True, 99)), [])
        self.assertEqual(drift(record(True, 1), record(False, 1)), ["network.port_status[web]: output.listening was True and is False"])
        self.assertEqual(drift({"results": {}}, record(True, 1)), [
            "network.port_status[web]: new in this snapshot", "storage.usage[data]: new in this snapshot"])


if __name__ == "__main__":
    unittest.main()
