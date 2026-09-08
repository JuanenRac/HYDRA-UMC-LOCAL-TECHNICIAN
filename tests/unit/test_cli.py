# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from pathlib import Path
import unittest

from hydra_umc_local_technician import __version__
from hydra_umc_local_technician.cli import main

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class ContractsValidateCommandTests(unittest.TestCase):
    def test_a_real_valid_fixture_exits_zero(self):
        exit_code = main(["contracts", "validate", str(FIXTURES / "tool_request.valid.json"), "--contract", "ToolRequest"])
        self.assertEqual(exit_code, 0)

    def test_a_real_invalid_fixture_exits_nonzero(self):
        exit_code = main(["contracts", "validate", str(FIXTURES / "tool_request.invalid.json"), "--contract", "ToolRequest"])
        self.assertEqual(exit_code, 1)

    def test_a_missing_file_exits_nonzero(self):
        exit_code = main(["contracts", "validate", "does-not-exist.json", "--contract", "ToolRequest"])
        self.assertEqual(exit_code, 1)


class VersionTests(unittest.TestCase):
    def test_version_flag_exits_zero(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_package_version_is_a_real_semver_triplet(self):
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(p.isdigit() for p in parts))


if __name__ == "__main__":
    unittest.main()
