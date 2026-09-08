# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_tool_matrix.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import unittest

from hydra_umc_local_technician.policy.risk_levels import RiskLevel
from hydra_umc_local_technician.policy.tool_matrix import TOOL_MATRIX, lookup_tool


class ToolMatrixTests(unittest.TestCase):
    def test_lookup_of_a_real_registered_tool_succeeds(self):
        descriptor = lookup_tool("service.status")
        self.assertIsNotNone(descriptor)
        self.assertEqual(descriptor.risk_level, RiskLevel.OBSERVE)

    def test_lookup_of_an_unregistered_tool_returns_none_not_a_default(self):
        self.assertIsNone(lookup_tool("does.not.exist"))
        self.assertIsNone(lookup_tool(""))

    def test_every_registered_tool_is_observe_level_in_this_phase(self):
        # Fase 0's own real scope - nothing above OBSERVE is registered
        # yet.
        for name, descriptor in TOOL_MATRIX.items():
            with self.subTest(tool=name):
                self.assertEqual(descriptor.risk_level, RiskLevel.OBSERVE)

    def test_descriptor_name_matches_its_own_dict_key(self):
        for key, descriptor in TOOL_MATRIX.items():
            self.assertEqual(key, descriptor.name)

    def test_every_descriptor_has_a_real_non_empty_description(self):
        for name, descriptor in TOOL_MATRIX.items():
            with self.subTest(tool=name):
                self.assertTrue(descriptor.description.strip())


if __name__ == "__main__":
    unittest.main()
