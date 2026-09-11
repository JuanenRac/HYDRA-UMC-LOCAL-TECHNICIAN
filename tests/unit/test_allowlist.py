# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_allowlist.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.orchestrator.allowlist import (
    OrchestratorConfig,
    PROJECT_NAME_PATTERN,
    UnknownAllowlistEntry,
    default_config,
)


class ResolveStoragePathTests(unittest.TestCase):
    def test_resolves_a_configured_name(self):
        config = OrchestratorConfig(storage_paths={"a": Path("/tmp/a")})
        self.assertEqual(config.resolve_storage_path("a"), Path("/tmp/a"))

    def test_refuses_an_unconfigured_name(self):
        config = OrchestratorConfig(storage_paths={"a": Path("/tmp/a")})
        with self.assertRaises(UnknownAllowlistEntry):
            config.resolve_storage_path("b")


class ResolvePortTests(unittest.TestCase):
    def test_resolves_a_configured_name(self):
        config = OrchestratorConfig(ports={"web": ("127.0.0.1", 8080)})
        self.assertEqual(config.resolve_port("web"), ("127.0.0.1", 8080))

    def test_refuses_an_unconfigured_name(self):
        config = OrchestratorConfig(ports={"web": ("127.0.0.1", 8080)})
        with self.assertRaises(UnknownAllowlistEntry):
            config.resolve_port("other")


class ResolveSystemdUnitTests(unittest.TestCase):
    def test_resolves_a_configured_unit(self):
        config = OrchestratorConfig(systemd_units=("hydra-umc-server",))
        self.assertEqual(config.resolve_systemd_unit("hydra-umc-server"), "hydra-umc-server")

    def test_refuses_an_unconfigured_unit(self):
        config = OrchestratorConfig(systemd_units=("hydra-umc-server",))
        with self.assertRaises(UnknownAllowlistEntry):
            config.resolve_systemd_unit("cron")


class ResolveProjectManifestPathTests(unittest.TestCase):
    def test_resolves_a_real_child_of_the_configured_root(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = OrchestratorConfig(ecosystem_root=root)
            resolved = config.resolve_project_manifest_path("HYDRA-UMC-SERVER")
            self.assertEqual(resolved, (root / "HYDRA-UMC-SERVER" / "hydra-umc.project.json").resolve())

    def test_refuses_when_no_root_is_configured(self):
        config = OrchestratorConfig()
        with self.assertRaises(UnknownAllowlistEntry):
            config.resolve_project_manifest_path("HYDRA-UMC-SERVER")

    def test_refuses_a_name_outside_the_real_project_naming_pattern(self):
        with TemporaryDirectory() as tmp:
            config = OrchestratorConfig(ecosystem_root=Path(tmp))
            for bad_name in ("../../etc", "lowercase-project", "HYDRA_UMC_SERVER", ""):
                with self.assertRaises(UnknownAllowlistEntry, msg=bad_name):
                    config.resolve_project_manifest_path(bad_name)

    def test_project_name_pattern_accepts_the_real_ecosystem_shapes(self):
        for good_name in ("HYDRA-UMC", "HYDRA-UMC-SERVER", "URTC", "URTC-FLASHER"):
            self.assertTrue(PROJECT_NAME_PATTERN.fullmatch(good_name), good_name)


class DefaultConfigTests(unittest.TestCase):
    def test_has_no_ecosystem_root_by_default(self):
        self.assertIsNone(default_config().ecosystem_root)

    def test_accepts_an_explicit_ecosystem_root(self):
        with TemporaryDirectory() as tmp:
            config = default_config(ecosystem_root=Path(tmp))
            self.assertEqual(config.ecosystem_root, Path(tmp))


if __name__ == "__main__":
    unittest.main()
