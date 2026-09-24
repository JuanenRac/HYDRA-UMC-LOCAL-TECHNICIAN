# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - execution mode and escalation outbox tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================

import tempfile
import unittest
from pathlib import Path

from hydra_umc_local_technician.escalation.outbox import EscalationOutbox
from hydra_umc_local_technician.policy.execution_mode import (
    DEFAULT_MODE,
    ApprovalRecord,
    ExecutionMode,
    decide,
)
from hydra_umc_local_technician.policy.risk_levels import RiskLevel


class ExecutionModeTests(unittest.TestCase):
    def test_the_default_is_diagnosis_only(self):
        self.assertIs(DEFAULT_MODE, ExecutionMode.DIAGNOSIS_ONLY)

    def test_read_only_actions_are_always_allowed(self):
        for mode in ExecutionMode:
            for level in (RiskLevel.INFORM, RiskLevel.OBSERVE):
                self.assertTrue(decide(mode, level, "storage.usage").allowed)

    def test_diagnosis_only_refuses_everything_above_observe_even_with_an_approval(self):
        approval = ApprovalRecord("operator", "service.restart", signature_verified=True)
        for level in (RiskLevel.PREPARE, RiskLevel.REVERSIBLE_OPERATION, RiskLevel.PRIVILEGED_CHANGE, RiskLevel.PHYSICAL_ACTION):
            self.assertFalse(decide(ExecutionMode.DIAGNOSIS_ONLY, level, "service.restart", approval).allowed, level)

    def test_assisted_needs_a_named_verified_approval_for_that_exact_action(self):
        level = RiskLevel.REVERSIBLE_OPERATION
        self.assertFalse(decide(ExecutionMode.ASSISTED, level, "service.restart").allowed)
        self.assertFalse(decide(ExecutionMode.ASSISTED, level, "service.restart", ApprovalRecord("", "service.restart", True)).allowed)
        self.assertFalse(decide(ExecutionMode.ASSISTED, level, "service.restart", ApprovalRecord("op", "service.stop", True)).allowed)
        self.assertFalse(decide(ExecutionMode.ASSISTED, level, "service.restart", ApprovalRecord("op", "service.restart", False)).allowed)
        self.assertTrue(decide(ExecutionMode.ASSISTED, level, "service.restart", ApprovalRecord("op", "service.restart", True)).allowed)


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.outbox = EscalationOutbox(Path(self._tmp.name))

    def test_an_escalation_survives_a_restart_while_the_link_is_down(self):
        self.outbox.enqueue("inc-1", {"summary": "disk full"})
        reopened = EscalationOutbox(Path(self._tmp.name))
        self.assertEqual([q.escalation_id for q in reopened.pending()], ["inc-1"])
        self.assertEqual(reopened.pending()[0].payload, {"summary": "disk full"})

    def test_a_failed_send_keeps_the_item_and_stops_the_run(self):
        self.outbox.enqueue("a", {})
        self.outbox.enqueue("b", {})
        self.assertEqual(self.outbox.flush(lambda item: False), 0)
        self.assertEqual(len(self.outbox.pending()), 2)

    def test_a_network_error_is_treated_as_not_sent(self):
        self.outbox.enqueue("a", {})

        def down(item):
            raise ConnectionError("unreachable")

        self.assertEqual(self.outbox.flush(down), 0)
        self.assertEqual(len(self.outbox.pending()), 1)

    def test_confirmed_items_move_to_sent_and_are_never_sent_again(self):
        self.outbox.enqueue("a", {})
        sent_ids = []
        self.assertEqual(self.outbox.flush(lambda item: sent_ids.append(item.escalation_id) or True), 1)
        self.assertEqual(self.outbox.flush(lambda item: sent_ids.append(item.escalation_id) or True), 0)
        self.assertEqual(sent_ids, ["a"])

    def test_queueing_the_same_id_twice_does_not_duplicate_it(self):
        self.outbox.enqueue("a", {"n": 1})
        self.outbox.enqueue("a", {"n": 2})
        self.assertEqual(self.outbox.pending()[0].payload, {"n": 1})
        self.outbox.flush(lambda item: True)
        self.outbox.enqueue("a", {"n": 3})
        self.assertEqual(self.outbox.pending(), [])

    def test_unsafe_ids_are_refused(self):
        for bad in ("../x", "a/b", "", ".hidden"):
            with self.assertRaises(ValueError):
                self.outbox.enqueue(bad, {})


if __name__ == "__main__":
    unittest.main()
