# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_knowledge_store.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The chunks of the indexed files can be kept on disk between runs; closed unless configured, and never trusted when damaged."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from hydra_umc_local_technician.knowledge import index as knowledge_index
from hydra_umc_local_technician.settings import SettingsError, parse_settings


def _new_process() -> None:
    """What a second run starts with: nothing in memory."""
    knowledge_index.clear_caches()


class KnowledgeStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        knowledge_index.clear_caches()
        self.addCleanup(knowledge_index.configure_persistence, None)
        self.addCleanup(knowledge_index.clear_caches)

    def test_closed_by_default_nothing_is_written(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp, "docs")
            root.mkdir()
            (root / "a.md").write_text("# Bus\ntermination", encoding="utf-8")
            knowledge_index.cached_index(root)
            self.assertEqual(list(Path(tmp).glob("**/knowledge-*.json")), [])

    def test_a_second_process_reads_only_the_files_that_changed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp, "docs")
            store = Path(tmp, "store")
            root.mkdir()
            (root / "a.md").write_text("# Bus\ntermination of the CAN bus", encoding="utf-8")
            (root / "b.json").write_text('{"name": "x"}', encoding="utf-8")
            knowledge_index.configure_persistence(store)
            first, _ = knowledge_index.cached_index(root)
            self.assertEqual(len(list(store.glob("knowledge-*.json"))), 1)
            _new_process()
            knowledge_index.configure_persistence(store)
            reads: list[str] = []
            original = Path.read_text

            def counting(self: Path, *args: object, **kwargs: object) -> str:
                reads.append(self.name)
                return original(self, *args, **kwargs)  # type: ignore[arg-type]

            with mock.patch.object(Path, "read_text", counting):
                second, index = knowledge_index.cached_index(root)
            self.assertEqual([name for name in reads if name in ("a.md", "b.json")], [])
            self.assertEqual(second.indexed_sources, first.indexed_sources)
            self.assertTrue(knowledge_index.search(index, "termination"))

    def test_a_changed_file_is_read_again_and_a_vanished_one_leaves_the_store(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp, "docs")
            store = Path(tmp, "store")
            root.mkdir()
            (root / "a.md").write_text("# Bus\ntermination", encoding="utf-8")
            (root / "b.md").write_text("# Arm\ngripper", encoding="utf-8")
            knowledge_index.configure_persistence(store)
            knowledge_index.cached_index(root)
            _new_process()
            knowledge_index.configure_persistence(store)
            (root / "a.md").write_text("# Bus\nthe terminator is now a longer text", encoding="utf-8")
            (root / "b.md").unlink()
            _, index = knowledge_index.cached_index(root)
            self.assertTrue(knowledge_index.search(index, "terminator"))
            self.assertFalse(knowledge_index.search(index, "gripper"))
            saved = json.loads(next(store.glob("knowledge-*.json")).read_text(encoding="utf-8"))
            self.assertEqual(sorted(saved["files"]), ["a.md"])

    def test_a_damaged_or_foreign_store_is_ignored_and_made_again(self) -> None:
        for content in ("not json", '{"format": 99, "root": "x", "files": {}}', '{"format": 1, "root": "other", "files": {"a.md": [1, 2, []]}}', '[]'):
            with self.subTest(content=content), TemporaryDirectory() as tmp:
                root = Path(tmp, "docs")
                store = Path(tmp, "store")
                root.mkdir()
                store.mkdir()
                (root / "a.md").write_text("# Bus\ntermination", encoding="utf-8")
                knowledge_index.clear_caches()
                knowledge_index.configure_persistence(store)
                path = knowledge_index._store_path(str(root.resolve()))
                assert path is not None
                path.write_text(content, encoding="utf-8")
                _, index = knowledge_index.cached_index(root)
                self.assertTrue(knowledge_index.search(index, "termination"))
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["format"], knowledge_index.STORE_FORMAT)

    def test_the_settings_section_is_closed_and_checked(self) -> None:
        self.assertFalse(parse_settings({}).knowledge.enabled)
        with self.assertRaises(SettingsError):
            parse_settings({"knowledge": {"enabled": True}})
        with self.assertRaises(SettingsError):
            parse_settings({"knowledge": {"enabled": True, "directory": "relative"}})
        with self.assertRaises(SettingsError):
            parse_settings({"knowledge": {"enabled": True, "directory": str(Path("/x").resolve()), "bogus": 1}})
        ok = parse_settings({"knowledge": {"enabled": True, "directory": str(Path("/x").resolve()), "maxStoredFiles": 10}})
        self.assertEqual(ok.knowledge.max_stored_files, 10)


if __name__ == "__main__":
    unittest.main()
