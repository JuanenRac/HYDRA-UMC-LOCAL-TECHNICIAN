# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_knowledge_byte_order_mark.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Knowledge files saved with a byte-order mark."""
from __future__ import annotations

from hydra_umc_local_technician.knowledge.index import ingest_source_directory


def test_files_with_a_byte_order_mark_are_indexed(tmp_path):
    (tmp_path / "manifest.json").write_bytes(b'\xef\xbb\xbf{"name": "demo"}')
    (tmp_path / "guide.md").write_bytes("\ufeff# Paro\n\ntexto\n".encode("utf-8"))
    result = ingest_source_directory(tmp_path)
    assert not result.skipped_sources
    assert sorted(chunk.kind for chunk in result.chunks) == ["json", "markdown"]
    assert [chunk.heading for chunk in result.chunks if chunk.kind == "markdown"] == ["Paro"]
