# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/test_secret_file_encodings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A secret file saved by an editor of Windows with a byte order mark holds the same secret; a file in another encoding is refused, never guessed."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hydra_umc_local_technician.assistant import AssistantError, read_key
from hydra_umc_local_technician.escalation.transport import TransportError, read_node_token
from hydra_umc_local_technician.webapi import read_api_token

SAMPLE = "sample-0123456789-abcdefghij-0123456789-xyz"


class SecretFileEncodingTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.bom = Path(folder.name, "bom.token")
        self.bom.write_bytes(b"\xef\xbb\xbf" + SAMPLE.encode("ascii") + b"\r\n")  # what Notepad calls "UTF-8 with BOM"
        self.utf16 = Path(folder.name, "utf16.token")
        self.utf16.write_bytes((SAMPLE + "\r\n").encode("utf-16"))  # what `>` of Windows PowerShell writes

    def test_the_assistant_key_ignores_a_byte_order_mark(self) -> None:
        self.assertEqual(read_key(SimpleNamespace(api_key_file=str(self.bom), api_key_env="UNSET"), {}), SAMPLE)

    def test_the_assistant_key_refuses_another_encoding(self) -> None:
        with self.assertRaises(AssistantError):
            read_key(SimpleNamespace(api_key_file=str(self.utf16), api_key_env="UNSET"), {})

    def test_the_node_token_ignores_a_byte_order_mark(self) -> None:
        self.assertEqual(read_node_token(SimpleNamespace(node_token_file=str(self.bom), require_node_token=True)), SAMPLE)

    def test_the_node_token_refuses_another_encoding(self) -> None:
        with self.assertRaises(TransportError):
            read_node_token(SimpleNamespace(node_token_file=str(self.utf16), require_node_token=True))

    def test_the_api_token_ignores_a_byte_order_mark(self) -> None:
        self.assertEqual(read_api_token(str(self.bom), {}), SAMPLE)

    def test_the_api_token_refuses_another_encoding(self) -> None:
        with self.assertRaises(ValueError):
            read_api_token(str(self.utf16), {})


if __name__ == "__main__":
    unittest.main()
