# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_knowledge_cache.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The index is kept between searches of one process, and never outlives a change of the files it was made from."""
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from hydra_umc_local_technician.knowledge import index as knowledge_index


def _write(path: Path, text: str, *, bump_ns: int = 0) -> None:
    path.write_text(text, encoding="utf-8")
    if bump_ns:
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + bump_ns))


class CachedIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        knowledge_index.clear_caches()
        self.addCleanup(knowledge_index.clear_caches)

    def test_an_unchanged_root_gives_the_same_index_without_reading_the_files_again(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "a.md", "# Bus\nCAN bus termination is 120 ohm.")
            _write(root / "b.json", '{"name": "x"}')
            first_ingest, first_index = knowledge_index.cached_index(root)
            reads = []
            original = Path.read_text

            def counting(self, *args, **kwargs):
                reads.append(self.name)
                return original(self, *args, **kwargs)

            with mock.patch.object(Path, "read_text", counting):
                second_ingest, second_index = knowledge_index.cached_index(root)
            self.assertIs(second_index, first_index)
            self.assertEqual(reads, [])
            self.assertEqual(second_ingest.indexed_sources, first_ingest.indexed_sources)

    def test_an_edited_file_is_read_again_and_the_index_follows(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "a.md", "# Bus\ntermination of the CAN bus")
            _, before = knowledge_index.cached_index(root)
            self.assertTrue(knowledge_index.search(before, "termination"))
            self.assertFalse(knowledge_index.search(before, "gripper"))
            _write(root / "a.md", "# Bus\nthe gripper closes slowly now, longer text", bump_ns=5_000_000)
            _, after = knowledge_index.cached_index(root)
            self.assertIsNot(after, before)
            self.assertTrue(knowledge_index.search(after, "gripper"))
            self.assertFalse(knowledge_index.search(after, "termination"))

    def test_a_file_that_appears_or_vanishes_changes_the_index(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "a.md", "# One\nfirst document")
            ingest_one, index_one = knowledge_index.cached_index(root)
            _write(root / "b.md", "# Two\nsecond document about hydraulics")
            ingest_two, index_two = knowledge_index.cached_index(root)
            self.assertIsNot(index_two, index_one)
            self.assertEqual(len(ingest_two.indexed_sources), len(ingest_one.indexed_sources) + 1)
            (root / "b.md").unlink()
            ingest_three, index_three = knowledge_index.cached_index(root)
            self.assertEqual(ingest_three.indexed_sources, ingest_one.indexed_sources)
            self.assertFalse(knowledge_index.search(index_three, "hydraulics"))

    def test_two_roots_do_not_share_an_index(self) -> None:
        with TemporaryDirectory() as one, TemporaryDirectory() as two:
            _write(Path(one) / "a.md", "# A\nalpha document")
            _write(Path(two) / "a.md", "# A\nbeta document")
            _, index_one = knowledge_index.cached_index(Path(one))
            _, index_two = knowledge_index.cached_index(Path(two))
            self.assertTrue(knowledge_index.search(index_one, "alpha"))
            self.assertFalse(knowledge_index.search(index_two, "alpha"))
            self.assertTrue(knowledge_index.search(index_two, "beta"))

    def test_the_file_cache_is_bounded(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for number in range(8):
                _write(root / f"f{number}.md", f"# H{number}\ntext number {number}")
            with mock.patch.object(knowledge_index, "MAX_CACHED_FILES", 3):
                knowledge_index.ingest_source_directory(root)
            self.assertLessEqual(len(knowledge_index._FILE_CACHE), 3)

    def test_a_missing_root_is_empty_not_an_error(self) -> None:
        with TemporaryDirectory() as tmp:
            ingested, index = knowledge_index.cached_index(Path(tmp) / "nowhere")
            self.assertEqual(ingested.chunks, ())
            self.assertEqual(knowledge_index.search(index, "anything"), [])


if __name__ == "__main__":
    unittest.main()
