# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_default_config_against_os.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The default allow-list against what the installer of the operating-system project lays down (and the server that is installed).

`default_config()` describes a Compute Module 5 installation. Nobody has checked it on a board yet; what can be checked without one is that every
entry agrees with the files that decide that installation: the folder and the unit that `install_server.sh` writes, the port of the registry of ports,
and the route that the server answers. The tests need the checkouts of HYDRA-UMC-OS and HYDRA-UMC-SERVER next to this one (or named by
HYDRA_UMC_OS_DIR and HYDRA_UMC_SERVER_DIR) and are skipped, saying why, when they are not there. They are run by the manual workflow "Default allow-list
against the installer".
"""
import os
import re
import unittest
from pathlib import Path

from hydra_umc_local_technician.orchestrator.allowlist import default_config

HERE = Path(__file__).resolve().parent.parent.parent


def _sibling(variable: str, name: str) -> Path | None:
    chosen = os.environ.get(variable)
    path = Path(chosen) if chosen else HERE.parent / name
    return path if path.is_dir() else None


OS_DIR = _sibling("HYDRA_UMC_OS_DIR", "HYDRA-UMC-OS")
SERVER_DIR = _sibling("HYDRA_UMC_SERVER_DIR", "HYDRA-UMC-SERVER")


def _text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", "replace").replace("\r\n", "\n")


@unittest.skipIf(OS_DIR is None, "the checkout of HYDRA-UMC-OS is not next to this one")
class DefaultConfigAgainstTheInstaller(unittest.TestCase):
    def setUp(self) -> None:
        assert OS_DIR is not None
        self.config = default_config()
        self.installer = _text(OS_DIR / "provisioning" / "install_server.sh")
        self.ports = _text(OS_DIR / "provisioning" / "ports.yaml")

    def _target(self) -> str:
        found = re.search(r"^TARGET=(\S+)$", self.installer, re.MULTILINE)
        self.assertIsNotNone(found, "install_server.sh names its TARGET folder")
        assert found is not None
        return found.group(1)

    def test_the_data_folder_and_the_log_are_inside_the_folder_the_installer_makes(self) -> None:
        target = Path(self._target())
        data = self.config.storage_paths["server_data"]
        log = self.config.log_sources["server_log"]
        self.assertTrue(data.is_relative_to(target), f"{data} is not under {target}")
        self.assertTrue(log.is_relative_to(data), f"{log} is not under {data}")

    def test_every_unit_of_the_list_is_a_unit_the_installer_writes(self) -> None:
        self.assertTrue(self.config.systemd_units)
        for unit in self.config.systemd_units:
            self.assertIn(f"{unit}.service", self.installer, f"install_server.sh does not write {unit}.service")

    def test_the_port_of_the_server_is_the_one_of_the_registry_of_ports(self) -> None:
        block = re.search(r"- name: HYDRA-UMC-SERVER\n\s+port: (\d+)\n(?:\s+health_path: (\S+)\n)?\s+systemd_unit: (\S+)", self.ports)
        self.assertIsNotNone(block, "ports.yaml has an entry for HYDRA-UMC-SERVER")
        assert block is not None
        host, port = self.config.ports["server_http"]
        self.assertEqual(port, int(block.group(1)))
        self.assertIn(host, ("127.0.0.1", "localhost"), "the allow-list only looks at the loopback")
        self.assertIn(block.group(3).removesuffix(".service"), self.config.systemd_units)
        for url in self.config.connectivity_targets.values():
            self.assertIn(f":{block.group(1)}/", url)

    def test_the_default_entries_name_nothing_outside_the_ecosystem_layout(self) -> None:
        for path in [*self.config.storage_paths.values(), *self.config.log_sources.values()]:
            self.assertTrue(path.as_posix().startswith("/opt/hydra-umc/"), path)
        for host, _port in self.config.ports.values():
            self.assertIn(host, ("127.0.0.1", "localhost"))
        for url in self.config.connectivity_targets.values():
            self.assertTrue(url.startswith("http://127.0.0.1:"), url)


@unittest.skipIf(SERVER_DIR is None, "the checkout of HYDRA-UMC-SERVER is not next to this one")
class DefaultConfigAgainstTheServer(unittest.TestCase):
    def test_the_route_the_connectivity_target_asks_for_exists_in_the_server(self) -> None:
        assert SERVER_DIR is not None
        routes = "".join(_text(path) for path in (SERVER_DIR / "src").rglob("*.ts"))
        for url in default_config().connectivity_targets.values():
            route = "/" + url.split("/", 3)[3]
            self.assertIn(route, routes, f"the server has no route {route}")

    def test_the_log_file_is_the_one_the_server_writes(self) -> None:
        assert SERVER_DIR is not None
        source = "".join(_text(path) for path in (SERVER_DIR / "src").glob("*.ts"))
        log = default_config().log_sources["server_log"]
        self.assertIn(log.name, source, "the server writes the log file the allow-list reads")
        self.assertIn("logs", source)


if __name__ == "__main__":
    unittest.main()
