# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_transport_scenarios.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The real outbox and the real HTTP sender against a simulated receiver that fails in every way a link and a server can fail."""
import json
import random
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.escalation.outbox import EscalationOutbox, QueuedEscalation
from hydra_umc_local_technician.escalation.transport import (
    CONTRACT_VERSION,
    MIN_NODE_TOKEN_LENGTH,
    MIN_SECRET_LENGTH,
    HttpSender,
    TransportError,
    build_message,
    check_url,
    read_node_token,
    read_secret,
    send_pending,
)
from hydra_umc_local_technician.settings import TransportSettings

SHARED = "k" * 32
TOKEN = "t" * 48


class SimulatedReceiver:
    """A stdlib HTTP server that plays a scripted list of behaviours, one per request, and records what it saw."""

    def __init__(self, script, port=0):
        owner = self
        self.script = list(script)
        self.seen: list[dict] = []
        self.headers: list[dict] = []
        self.redirect_hits = 0

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                owner.headers.append(dict(self.headers))
                try:
                    owner.seen.append(json.loads(raw))
                except ValueError:
                    owner.seen.append({})
                action = owner.script.pop(0) if owner.script else "ok"
                if action == "ok":
                    self._reply(200, b'{"ok": true}')
                elif action == "redirect":
                    self.send_response(307)
                    self.send_header("Location", f"http://127.0.0.1:{owner.port}/elsewhere")
                    self.end_headers()
                elif action == "slow":
                    time.sleep(1.5)
                    self._reply(200, b'{"ok": true}')
                elif action == "hangup":
                    self.connection.close()
                elif isinstance(action, tuple):
                    self._reply(*action)

            def do_GET(self):
                owner.redirect_hits += 1
                self._reply(200, b'{"ok": true}')

            def _reply(self, status, body):
                try:
                    self.send_response(status)
                    self.end_headers()
                    self.wfile.write(body)
                except OSError:
                    pass

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", port), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class TransportScenarios(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.outbox = EscalationOutbox(Path(self._tmp.name) / "outbox")
        self.env = {"HYDRA_UMC_LOCAL_TECHNICIAN_TRANSPORT_SECRET": SHARED}
        self.receivers: list[SimulatedReceiver] = []
        self.addCleanup(lambda: [r.stop() for r in self.receivers if r.thread.is_alive()])

    def receiver(self, script, port=0):
        receiver = SimulatedReceiver(script, port)
        self.receivers.append(receiver)
        return receiver

    def settings(self, receiver, **overrides):
        values = dict(enabled=True, url=f"http://127.0.0.1:{receiver.port}/incident", from_node="tec", to_node="dev",
                      require_node_token=False, timeout_seconds=1.0)
        values.update(overrides)
        return TransportSettings(**values)

    def queue(self, count):
        for n in range(count):
            self.outbox.enqueue(f"esc-{n}", {"n": n})

    def test_the_first_failure_stops_the_run_and_the_rest_waits_in_order(self):
        receiver = self.receiver(["ok", (503, b"busy"), "ok"])
        self.queue(3)
        settings = self.settings(receiver)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 1)
        self.assertEqual([q.escalation_id for q in self.outbox.pending()], ["esc-1", "esc-2"])
        self.assertEqual(send_pending(self.outbox, settings, self.env), 2)  # the link is back: the rest goes, in order
        self.assertEqual([m["payload"]["escalationId"] for m in receiver.seen], ["esc-0", "esc-1", "esc-1", "esc-2"])

    def test_a_retry_of_the_same_incident_keeps_its_id_and_changes_its_nonce(self):
        receiver = self.receiver([(500, b"{}"), "ok"])
        self.queue(1)
        settings = self.settings(receiver)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 0)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 1)
        first, second = receiver.seen
        self.assertEqual(first["message_id"], second["message_id"])
        self.assertNotEqual(first["nonce"], second["nonce"])
        self.assertNotEqual(first["mac"], second["mac"])

    def test_a_redirect_is_never_followed_and_the_body_goes_nowhere_else(self):
        receiver = self.receiver(["redirect"])
        self.queue(1)
        self.assertEqual(send_pending(self.outbox, self.settings(receiver), self.env), 0)
        self.assertEqual(receiver.redirect_hits, 0)
        self.assertEqual(len(self.outbox.pending()), 1)

    def test_a_server_that_hangs_up_or_answers_too_slowly_is_not_a_confirmation(self):
        receiver = self.receiver(["hangup", "slow"])
        self.queue(1)
        settings = self.settings(receiver, timeout_seconds=0.4)
        started = time.monotonic()
        self.assertEqual(send_pending(self.outbox, settings, self.env), 0)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 0)
        self.assertLess(time.monotonic() - started, 1.4)
        self.assertEqual(len(self.outbox.pending()), 1)

    def test_a_receiver_that_comes_back_on_the_same_address_gets_everything(self):
        first = self.receiver(["ok"])
        port = first.port
        self.queue(3)
        settings = self.settings(first)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 3)
        first.stop()
        self.outbox.enqueue("late-1", {"n": 100})
        self.outbox.enqueue("late-2", {"n": 101})
        self.assertEqual(send_pending(self.outbox, settings, self.env), 0)  # nobody is listening
        self.assertEqual(len(self.outbox.pending()), 2)
        second = self.receiver([], port=port)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 2)
        self.assertEqual([m["payload"]["escalationId"] for m in second.seen], ["late-1", "late-2"])
        self.assertEqual(self.outbox.pending(), [])

    def test_answers_that_are_not_a_plain_ok_are_all_refused(self):
        bodies = [b"", b"[]", b'{"ok": 1}', b'{"ok": null}', b'"ok"', b"\xff\xfe", b'{"ok": true']
        receiver = self.receiver([(200, body) for body in bodies])
        self.queue(1)
        settings = self.settings(receiver)
        for body in bodies:
            self.assertEqual(send_pending(self.outbox, settings, self.env), 0, body)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 1)

    def test_a_non_success_status_is_never_a_confirmation_even_with_an_ok_body(self):
        statuses = [201, 202]
        receiver = self.receiver([(s, b'{"ok": true}') for s in statuses] + [(s, b'{"ok": true}') for s in (404, 401, 500)])
        self.queue(5)
        settings = self.settings(receiver)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 2)  # any 2xx counts, the 404 stops the run
        self.assertEqual(len(self.outbox.pending()), 3)

    def test_a_payload_over_the_configured_limit_stays_queued_and_is_not_sent(self):
        receiver = self.receiver([])
        self.outbox.enqueue("big", {"blob": "x" * 5000})
        settings = self.settings(receiver, max_payload_bytes=1000)
        self.assertEqual(send_pending(self.outbox, settings, self.env), 0)
        self.assertEqual(receiver.seen, [])
        self.assertEqual(len(self.outbox.pending()), 1)

    def test_the_node_token_goes_only_as_a_bearer_header_and_never_in_the_body(self):
        token_file = Path(self._tmp.name) / "node.token"
        token_file.write_text(TOKEN + "\n", encoding="utf-8")
        receiver = self.receiver([])
        self.queue(1)
        settings = self.settings(receiver, require_node_token=True, node_token_file=str(token_file))
        self.assertEqual(send_pending(self.outbox, settings, self.env), 1)
        headers = {k.lower(): v for k, v in receiver.headers[0].items()}
        self.assertEqual(headers["authorization"], f"Bearer {TOKEN}")
        self.assertEqual(headers["x-hydra-client"], "technician")
        self.assertEqual(headers["content-type"], "application/json")
        self.assertNotIn(TOKEN, json.dumps(receiver.seen[0]))
        self.assertNotIn(SHARED, json.dumps(receiver.seen[0]))

    def test_without_a_token_no_authorization_header_is_sent(self):
        receiver = self.receiver([])
        self.queue(1)
        send_pending(self.outbox, self.settings(receiver), self.env)
        self.assertNotIn("authorization", {k.lower() for k in receiver.headers[0]})

    def test_a_closed_transport_or_a_missing_secret_sends_nothing(self):
        receiver = self.receiver([])
        self.queue(1)
        with self.assertRaisesRegex(TransportError, "closed"):
            send_pending(self.outbox, self.settings(receiver, enabled=False), self.env)
        with self.assertRaisesRegex(TransportError, "shorter"):
            send_pending(self.outbox, self.settings(receiver), {})
        with self.assertRaisesRegex(TransportError, "node token file is not set"):
            send_pending(self.outbox, self.settings(receiver, require_node_token=True), self.env)
        self.assertEqual(receiver.seen, [])
        self.assertEqual(len(self.outbox.pending()), 1)


class SecretsAndMessages(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_the_secret_comes_from_the_file_when_there_is_one_and_never_from_both(self):
        secret_file = self.dir / "secret"
        secret_file.write_text(f"  {SHARED}\n", encoding="utf-8")
        settings = TransportSettings(secret_file=str(secret_file))
        self.assertEqual(read_secret(settings, {settings.secret_env: "z" * 40}), SHARED)
        self.assertEqual(read_secret(TransportSettings(), {TransportSettings().secret_env: f" {SHARED} "}), SHARED)

    def test_a_short_missing_or_unreadable_secret_is_refused_without_echoing_it(self):
        short = "s" * (MIN_SECRET_LENGTH - 1)
        env_name = TransportSettings().secret_env
        with self.assertRaises(TransportError) as raised:
            read_secret(TransportSettings(), {env_name: short})
        self.assertNotIn(short, str(raised.exception))
        with self.assertRaises(TransportError):
            read_secret(TransportSettings(), {})
        with self.assertRaisesRegex(TransportError, "cannot read the transport secret file"):
            read_secret(TransportSettings(secret_file=str(self.dir / "absent")), {})
        read_secret(TransportSettings(), {env_name: "s" * MIN_SECRET_LENGTH})

    def test_the_node_token_rules(self):
        self.assertEqual(read_node_token(TransportSettings(require_node_token=False)), "")
        with self.assertRaisesRegex(TransportError, "not set"):
            read_node_token(TransportSettings(require_node_token=True))
        token_file = self.dir / "token"
        token_file.write_text("x" * (MIN_NODE_TOKEN_LENGTH - 1), encoding="utf-8")
        with self.assertRaisesRegex(TransportError, "shorter"):
            read_node_token(TransportSettings(node_token_file=str(token_file)))
        token_file.write_text("x" * MIN_NODE_TOKEN_LENGTH + "\n", encoding="utf-8")
        self.assertEqual(read_node_token(TransportSettings(node_token_file=str(token_file))), "x" * MIN_NODE_TOKEN_LENGTH)
        with self.assertRaisesRegex(TransportError, "cannot read the node token file"):
            read_node_token(TransportSettings(node_token_file=str(self.dir / "absent")))

    def test_check_url_refuses_what_could_leak_the_message(self):
        def settings(url, **extra):
            return TransportSettings(enabled=True, url=url, from_node="a", to_node="b", **extra)
        for bad in ("", "ftp://127.0.0.1/x", "http:///nohost", "file:///etc/passwd", "http://user:pass@127.0.0.1/x",
                    "http://example.org/x", "http://10.0.0.5/x"):
            with self.assertRaises(TransportError, msg=bad):
                check_url(settings(bad))
        for good in ("http://127.0.0.1:8/x", "http://localhost/x", "http://[::1]:9/x", "https://example.org/x"):
            check_url(settings(good))
        check_url(settings("http://10.0.0.5/x", allow_plain_http=True))
        with self.assertRaises(TransportError):
            check_url(settings("https://user@example.org/x", allow_plain_http=True))

    def test_the_sender_refuses_a_bad_address_before_anything_is_built(self):
        with self.assertRaises(TransportError):
            HttpSender(TransportSettings(url="http://example.org/x"), SHARED)

    def test_the_message_mac_covers_every_field_and_the_nonce_is_fresh(self):
        settings = TransportSettings(from_node="tec", to_node="dev")
        item = QueuedEscalation("e1", {"k": "v"})
        first = build_message(item, settings, SHARED, now=1.0)
        again = build_message(item, settings, SHARED, now=1.0)
        self.assertEqual((first["contract_version"], first["kind"], first["to_node"]), (CONTRACT_VERSION, "incident", "dev"))
        self.assertNotEqual(first["nonce"], again["nonce"])
        self.assertNotEqual(first["mac"], again["mac"])
        self.assertNotEqual(first["mac"], build_message(item, settings, "o" * 32, now=1.0)["mac"])
        self.assertEqual(len(first["mac"]), 64)
        self.assertEqual(len({build_message(item, settings, SHARED)["nonce"] for _ in range(50)}), 50)

    def test_random_payloads_survive_the_wire_unchanged(self):
        rng = random.Random(77)
        receiver = SimulatedReceiver([])
        self.addCleanup(receiver.stop)
        outbox = EscalationOutbox(self.dir / "outbox")
        sent = {}
        for n in range(25):
            payload = {"text": "".join(chr(rng.randrange(32, 0x2fff)) for _ in range(rng.randrange(1, 40))), "n": rng.randrange(10 ** 6),
                       "nested": {"list": [rng.random() for _ in range(3)]}}
            outbox.enqueue(f"r{n}", payload)
            sent[f"r{n}"] = payload
        settings = TransportSettings(enabled=True, url=f"http://127.0.0.1:{receiver.port}/x", from_node="a", to_node="b",
                                     require_node_token=False, timeout_seconds=2.0)
        self.assertEqual(send_pending(outbox, settings, {settings.secret_env: SHARED}), 25)
        got = {m["payload"]["escalationId"]: m["payload"]["evidenceBundle"] for m in receiver.seen}
        self.assertEqual(got, sent)


if __name__ == "__main__":
    unittest.main()
