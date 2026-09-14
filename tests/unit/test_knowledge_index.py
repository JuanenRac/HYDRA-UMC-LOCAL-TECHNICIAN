# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_knowledge_index.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 1's own real deliverable: the TF-IDF retrieval kernel ported from
HYDRA-UMC-DOCS-QA (tokenize/build_index/search, unchanged behavior) and
the new bounded, allow-list-root-scoped ingestion for real Markdown and
JSON sources. Same real `unittest.TestCase` + `tempfile.TemporaryDirectory`
convention every other module in this test suite already uses (see
test_dispatch.py's own real-temp-directory pattern) - real files on disk,
never a mocked filesystem.
"""
import unittest
import unittest.mock
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.knowledge.index import (
    KnowledgeChunk,
    build_index,
    ingest_source_directory,
    search,
    tokenize,
)


def _sample_chunks() -> list[KnowledgeChunk]:
    return [
        KnowledgeChunk(
            source="wiring.md", heading="CAN Bus Wiring",
            text="Twisted pair CAN bus wiring needs 120 ohm termination at both ends.",
            kind="markdown",
        ),
        KnowledgeChunk(
            source="firmware.md", heading="Firmware Flashing",
            text="Flash URTC firmware over SWD or JTAG using URTC-FLASHER.",
            kind="markdown",
        ),
    ]


class TokenizeTests(unittest.TestCase):
    def test_lowercases_and_strips_punctuation(self) -> None:
        self.assertEqual(tokenize("CAN-Bus Wiring!"), ["can", "bus", "wiring"])

    def test_keeps_accented_latin_words_whole(self) -> None:
        self.assertEqual(tokenize("Über Café Robôt niño"), ["über", "café", "robôt", "niño"])

    def test_splits_cjk_runs_into_overlapping_bigrams(self) -> None:
        self.assertEqual(tokenize("机器人"), ["机器", "器人"])


class SearchTests(unittest.TestCase):
    def test_ranks_matching_chunk_first(self) -> None:
        index = build_index(_sample_chunks())

        results = search(index, "CAN bus termination", top_k=3)

        self.assertTrue(results)
        self.assertEqual(results[0].chunk.heading, "CAN Bus Wiring")
        self.assertGreater(results[0].score, 0.0)

    def test_returns_empty_for_unrelated_query(self) -> None:
        index = build_index(_sample_chunks())

        self.assertEqual(search(index, "quantum entanglement lasagna", top_k=3), [])

    def test_rejects_negative_top_k(self) -> None:
        index = build_index(_sample_chunks())

        with self.assertRaises(ValueError):
            search(index, "CAN bus termination", top_k=-1)

    def test_build_index_on_empty_chunks_does_not_crash(self) -> None:
        index = build_index([])

        self.assertEqual(search(index, "anything", top_k=5), [])


class IngestSourceDirectoryTests(unittest.TestCase):
    def test_indexes_real_markdown_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Overview\n\nSome real prose about a robot arm.\n", encoding="utf-8"
            )
            result = ingest_source_directory(root)

            self.assertEqual(result.indexed_sources, ("README.md",))
            self.assertEqual(result.skipped_sources, ())
            self.assertFalse(result.truncated)
            self.assertEqual(len(result.chunks), 1)
            self.assertEqual(result.chunks[0].kind, "markdown")

    def test_indexes_real_json_manifests_as_one_chunk_each(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "hydra-umc.project.json").write_text(
                '{"name": "HYDRA-UMC-EXAMPLE", "version": "0.1.0"}', encoding="utf-8"
            )
            result = ingest_source_directory(root)

            self.assertEqual(result.indexed_sources, ("hydra-umc.project.json",))
            self.assertEqual(len(result.chunks), 1)
            self.assertEqual(result.chunks[0].kind, "json")
            self.assertIn("HYDRA-UMC-EXAMPLE", result.chunks[0].text)

    def test_skips_malformed_json_rather_than_indexing_raw_bytes(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken.json").write_text("{not valid json", encoding="utf-8")

            result = ingest_source_directory(root)

            self.assertEqual(result.indexed_sources, ())
            self.assertEqual(result.skipped_sources, ("broken.json",))

    def test_rejects_disallowed_extensions(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "secret.env").write_text("TOKEN=abc123", encoding="utf-8")
            (root / "notes.txt").write_text("plain text, not markdown", encoding="utf-8")

            result = ingest_source_directory(root)

            self.assertEqual(result.indexed_sources, ())
            self.assertEqual(result.chunks, ())

    def test_skips_a_file_over_the_real_size_cap(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "big.md").write_text(
                "# Heading\n\nThis body is longer than ten bytes.\n", encoding="utf-8"
            )
            with unittest.mock.patch(
                "hydra_umc_local_technician.knowledge.index.MAX_DOCUMENT_BYTES", 10
            ):
                result = ingest_source_directory(root)

            self.assertEqual(result.indexed_sources, ())
            self.assertEqual(result.skipped_sources, ("big.md",))

    def test_bounds_the_real_file_count_and_reports_truncation(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(4):
                (root / f"doc-{i}.md").write_text(f"# Doc {i}\n\nReal content {i}.\n", encoding="utf-8")

            with unittest.mock.patch(
                "hydra_umc_local_technician.knowledge.index.MAX_INDEXED_FILES", 2
            ):
                result = ingest_source_directory(root)

            self.assertEqual(len(result.indexed_sources), 2)
            self.assertTrue(result.truncated)

    def test_walks_real_subdirectories(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "docs" / "guides"
            nested.mkdir(parents=True)
            (nested / "install.md").write_text("# Install\n\nReal install steps.\n", encoding="utf-8")

            result = ingest_source_directory(root)

            self.assertEqual(result.indexed_sources, ("docs/guides/install.md",))

    def test_of_a_missing_root_is_a_real_empty_result_not_an_error(self) -> None:
        with TemporaryDirectory() as tmp:
            result = ingest_source_directory(Path(tmp) / "does-not-exist")

            self.assertEqual(result.chunks, ())
            self.assertEqual(result.indexed_sources, ())
            self.assertFalse(result.truncated)

    def test_end_to_end_ingest_then_search_finds_the_real_relevant_document(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CAN_WIRING.md").write_text(
                "# CAN Bus Wiring\n\nTwisted pair CAN bus wiring needs 120 ohm termination.\n",
                encoding="utf-8",
            )
            (root / "FIRMWARE.md").write_text(
                "# Firmware Flashing\n\nFlash URTC firmware over SWD or JTAG.\n",
                encoding="utf-8",
            )

            result = ingest_source_directory(root)
            index = build_index(list(result.chunks))
            results = search(index, "CAN bus termination wiring", top_k=2)

            self.assertTrue(results)
            self.assertEqual(results[0].chunk.source, "CAN_WIRING.md")


if __name__ == "__main__":
    unittest.main()
