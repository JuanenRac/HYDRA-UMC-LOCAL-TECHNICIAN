# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_outbox_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The escalation outbox under crashes and clashes: nothing is deleted, nothing is sent twice, nothing set aside is lost."""
import json
import os
import random
import tempfile
import unittest
from pathlib import Path

from hydra_umc_local_technician.escalation import outbox as outbox_module
from hydra_umc_local_technician.escalation.outbox import (
    CONFLICT,
    DUPLICATE,
    QUEUED,
    STALE_TEMPORARY_SECONDS,
    EscalationOutbox,
)


class OutboxEdges(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.outbox = EscalationOutbox(self.root)

    def corrupt_names(self):
        folder = self.root / "corrupt"
        return sorted(p.name for p in folder.iterdir()) if folder.exists() else []

    def test_enqueue_says_what_happened(self):
        self.assertEqual(self.outbox.enqueue("a", {"n": 1}), QUEUED)
        self.assertEqual(self.outbox.enqueue("a", {"n": 1}), DUPLICATE)
        self.assertEqual(self.outbox.enqueue("a", {"n": 2}), CONFLICT)
        self.assertEqual(self.outbox.pending()[0].payload, {"n": 1})
        self.assertEqual(self.corrupt_names(), ["a.conflict.json"])

    def test_every_clash_is_kept_and_none_overwrites_another(self):
        self.outbox.enqueue("a", {"n": 0})
        for n in (1, 2, 3):
            self.assertEqual(self.outbox.enqueue("a", {"n": n}), CONFLICT)
        self.assertEqual(self.corrupt_names(), ["a.conflict.1.json", "a.conflict.2.json", "a.conflict.json"])
        kept = sorted(json.loads((self.root / "corrupt" / name).read_text(encoding="utf-8"))["n"] for name in self.corrupt_names())
        self.assertEqual(kept, [1, 2, 3])

    def test_a_clash_with_something_already_sent_is_found_too(self):
        self.outbox.enqueue("a", {"n": 1})
        self.outbox.flush(lambda item: True)
        self.assertEqual(self.outbox.enqueue("a", {"n": 1}), DUPLICATE)
        self.assertEqual(self.outbox.enqueue("a", {"n": 9}), CONFLICT)
        self.assertEqual(self.outbox.pending(), [])

    def test_the_payload_key_order_does_not_make_a_duplicate_look_new(self):
        self.outbox.enqueue("a", {"x": 1, "y": 2})
        self.assertEqual(self.outbox.enqueue("a", {"y": 2, "x": 1}), DUPLICATE)

    def test_an_existing_file_that_cannot_be_read_counts_as_a_conflict(self):
        (self.root / "pending" / "a.json").write_text("{broken", encoding="utf-8")
        self.assertEqual(self.outbox.enqueue("a", {"n": 1}), CONFLICT)

    def test_a_payload_that_cannot_be_written_leaves_no_temporary_file(self):
        with self.assertRaises(TypeError):
            self.outbox.enqueue("a", {"bad": object()})
        self.assertEqual(list((self.root / "pending").iterdir()), [])
        self.assertEqual(self.outbox.pending(), [])

    def test_unsafe_ids_are_refused_everywhere(self):
        for bad in ("../x", "a/b", "", ".hidden", "-lead", "a" * 82, "a b", "a\\b"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.outbox.enqueue(bad, {})
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.outbox.mark_sent(bad)
        longest = "a" * 81
        self.assertEqual(self.outbox.enqueue(longest, {}), QUEUED)

    def test_unreadable_entries_are_set_aside_and_the_rest_still_flows(self):
        self.outbox.enqueue("good", {"n": 1})
        pending = self.root / "pending"
        (pending / "bad.json").write_text("{nope", encoding="utf-8")
        (pending / "list.json").write_text("[1]", encoding="utf-8")
        (pending / "a b.json").write_text("{}", encoding="utf-8")
        self.assertEqual([q.escalation_id for q in self.outbox.pending()], ["good"])
        self.assertEqual(self.corrupt_names(), ["a b.json", "bad.json", "list.json"])
        self.assertEqual(sorted(p.name for p in pending.iterdir()), ["good.json"])

    def test_two_entries_set_aside_with_the_same_name_do_not_overwrite_each_other(self):
        for text in ("{one", "{two"):
            (self.root / "pending" / "bad.json").write_text(text, encoding="utf-8")
            self.outbox.pending()
        self.assertEqual(self.corrupt_names(), ["bad.1.json", "bad.json"])
        contents = sorted((self.root / "corrupt" / name).read_text(encoding="utf-8") for name in self.corrupt_names())
        self.assertEqual(contents, ["{one", "{two"])

    def test_a_temporary_file_is_left_alone_while_it_is_young_and_set_aside_when_stale(self):
        young = self.root / "pending" / "young.tmp"
        old = self.root / "pending" / "old.tmp"
        young.write_text("half", encoding="utf-8")
        old.write_text("half", encoding="utf-8")
        now = young.stat().st_mtime + STALE_TEMPORARY_SECONDS + 5
        os.utime(young, (now - 10, now - 10))
        self.assertEqual(self.outbox.set_aside_stale_temporaries(now=now), 1)
        self.assertTrue(young.exists())
        self.assertFalse(old.exists())
        self.assertEqual(self.corrupt_names(), ["old.tmp"])
        self.assertEqual(self.outbox.set_aside_stale_temporaries(now=now), 0)

    def test_reopening_the_queue_sets_aside_what_a_dead_process_left(self):
        left = self.root / "pending" / "dead.tmp"
        left.write_text("half", encoding="utf-8")
        long_ago = left.stat().st_mtime - 3 * STALE_TEMPORARY_SECONDS
        os.utime(left, (long_ago, long_ago))
        EscalationOutbox(self.root)
        self.assertFalse(left.exists())
        self.assertEqual(self.corrupt_names(), ["dead.tmp"])

    def test_mark_sent_is_idempotent_and_never_overwrites_the_record_of_what_was_sent(self):
        self.outbox.mark_sent("never-queued")  # nothing to do, no error
        self.outbox.enqueue("a", {"n": 1})
        self.outbox.mark_sent("a")
        sent = self.root / "sent" / "a.json"
        self.assertEqual(json.loads(sent.read_text(encoding="utf-8")), {"n": 1})
        # a crash between two steps: the same id is pending again while the record of the send exists
        (self.root / "pending" / "a.json").write_text(json.dumps({"n": 2}), encoding="utf-8")
        self.outbox.mark_sent("a")
        self.assertEqual(json.loads(sent.read_text(encoding="utf-8")), {"n": 1})
        self.assertEqual(self.outbox.pending(), [])
        self.assertEqual(self.corrupt_names(), ["a.json"])

    def test_flush_stops_at_the_first_failure_and_keeps_the_order(self):
        for name in ("c", "a", "b"):
            self.outbox.enqueue(name, {"id": name})
        order = []

        def send(item):
            order.append(item.escalation_id)
            return item.escalation_id != "b"

        self.assertEqual(self.outbox.flush(send), 1)
        self.assertEqual(order, ["a", "b"])
        self.assertEqual([q.escalation_id for q in self.outbox.pending()], ["b", "c"])

    def test_a_filesystem_without_hard_links_still_queues_the_entry(self):
        real_link = os.link

        def refuse(*args, **kwargs):
            raise OSError("no hard links here")

        outbox_module.os.link = refuse  # type: ignore[assignment]
        try:
            self.assertEqual(self.outbox.enqueue("a", {"n": 1}), QUEUED)
        finally:
            outbox_module.os.link = real_link
        self.assertEqual(self.outbox.pending()[0].payload, {"n": 1})
        self.assertEqual([p.name for p in (self.root / "pending").iterdir()], ["a.json"])

    def test_random_traffic_never_loses_or_duplicates_an_entry(self):
        rng = random.Random(4242)
        queued: dict[str, dict] = {}
        for _ in range(120):
            name = f"id{rng.randrange(15)}"
            payload = {"n": rng.randrange(3)}
            answer = self.outbox.enqueue(name, payload)
            if name not in queued:
                self.assertEqual(answer, QUEUED)
                queued[name] = payload
            else:
                self.assertEqual(answer, DUPLICATE if queued[name] == payload else CONFLICT)
        self.assertEqual({q.escalation_id: q.payload for q in self.outbox.pending()}, queued)
        sent = []
        self.assertEqual(self.outbox.flush(lambda item: sent.append(item.escalation_id) or True), len(queued))
        self.assertEqual(sorted(sent), sorted(queued))
        self.assertEqual(self.outbox.pending(), [])


if __name__ == "__main__":
    unittest.main()
