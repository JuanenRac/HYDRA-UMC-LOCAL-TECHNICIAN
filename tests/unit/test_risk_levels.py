# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_risk_levels.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import unittest

from hydra_umc_local_technician.policy.risk_levels import POLICIES, RiskLevel


class RiskLevelOrderingTests(unittest.TestCase):
    def test_levels_are_ordered_from_least_to_most_risky(self):
        ordered = [
            RiskLevel.INFORM, RiskLevel.OBSERVE, RiskLevel.PREPARE,
            RiskLevel.REVERSIBLE_OPERATION, RiskLevel.PRIVILEGED_CHANGE,
            RiskLevel.PHYSICAL_ACTION,
        ]
        for lower, higher in zip(ordered, ordered[1:]):
            self.assertLess(lower, higher)

    def test_wire_name_round_trips(self):
        for level in RiskLevel:
            self.assertEqual(RiskLevel.from_wire_name(level.wire_name), level)

    def test_an_unknown_wire_name_is_rejected(self):
        with self.assertRaises(ValueError):
            RiskLevel.from_wire_name("super_admin_mode")


class RiskLevelPolicyTests(unittest.TestCase):
    def test_every_level_has_a_real_policy_entry(self):
        for level in RiskLevel:
            self.assertIn(level, POLICIES)

    def test_inform_cannot_read_any_tool(self):
        self.assertFalse(POLICIES[RiskLevel.INFORM].can_read_tools)

    def test_only_reversible_operation_and_above_can_mutate(self):
        for level in (RiskLevel.INFORM, RiskLevel.OBSERVE, RiskLevel.PREPARE):
            self.assertFalse(POLICIES[level].can_mutate, f"{level} must never mutate")
        for level in (RiskLevel.REVERSIBLE_OPERATION, RiskLevel.PRIVILEGED_CHANGE, RiskLevel.PHYSICAL_ACTION):
            self.assertTrue(POLICIES[level].can_mutate, f"{level} is defined as mutating")

    def test_the_two_highest_levels_are_explicitly_not_implemented(self):
        # Fase 0's own real boundary: declared for contract completeness,
        # never implemented in this codebase.
        self.assertFalse(POLICIES[RiskLevel.PRIVILEGED_CHANGE].implemented)
        self.assertFalse(POLICIES[RiskLevel.PHYSICAL_ACTION].implemented)

    def test_observe_is_implemented_as_a_policy_even_though_no_tool_is_wired_yet(self):
        # The POLICY exists and is real; policy != a live tool handler -
        # see tool_matrix.py's own per-tool `implemented` flag for that.
        self.assertTrue(POLICIES[RiskLevel.OBSERVE].implemented)


if __name__ == "__main__":
    unittest.main()
