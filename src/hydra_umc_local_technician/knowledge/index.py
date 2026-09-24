# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/knowledge/index.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 1: a real, local index of approved documentation, manifests,
contracts and runbooks - never trained blindly on the whole disk.

The retrieval kernel (tokenize/TF-IDF/cosine search) is the same real,
tested, stdlib-only design HYDRA-UMC-DOCS-QA's own `index.py` already
uses - ported, not imported cross-repo (this project stays independent,
same real logic, same real property this whole ecosystem already
follows for shared-but-not-centralized code, e.g.
`knowledge/redaction.py`'s own port from HYDRA-UMC-OPS-AGENT). What is
new here is the source: DOCS-QA only ever ingests `.md`/`.markdown`;
this technician's own Fase 1 scope explicitly also needs manifests
(`hydra-umc.project.json`) and contracts (`*.schema.json`) - real JSON,
never prose - so each JSON file becomes exactly one real chunk (its own
pretty-printed text), rather than forcing a heading-based chunker that
JSON has no real notion of onto it.

Every real search this module ever runs is scoped to ONE, real,
already-allow-listed root directory (see `orchestrator/allowlist.py`'s
own `resolve_knowledge_source` - the same "symbolic name, not a raw
path a caller supplies" boundary every other OBSERVE tool already
uses), and the walk itself is bounded (file count, total bytes) so even
a legitimately allow-listed root cannot turn into an unbounded read.
The index is built fresh on every real call, same as `manifest.read`
re-reads its own JSON fresh every time - there is no long-running
process yet to usefully cache it in (a later phase's own concern, not
invented here without one).
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# Same real accented-Latin + CJK-bigram tokenizer HYDRA-UMC-DOCS-QA's own
# index.py already established and tested - this technician's
# own docs are written in the same 7 languages as every other repo in
# this ecosystem.
_LATIN_TOKEN_RE = re.compile(r"[a-z0-9À-ɏ]+")
_CJK_RUN_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]+")
_SCAN_RE = re.compile(f"{_CJK_RUN_RE.pattern}|{_LATIN_TOKEN_RE.pattern}")


def _cjk_bigrams(run: str) -> list[str]:
    if len(run) < 2:
        return [run]
    return [run[i : i + 2] for i in range(len(run) - 1)]


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens: list[str] = []
    for match in _SCAN_RE.finditer(text):
        run = match.group(0)
        if _CJK_RUN_RE.fullmatch(run):
            tokens.extend(_cjk_bigrams(run))
        else:
            tokens.append(run)
    return tokens


@dataclass(frozen=True)
class KnowledgeChunk:
    """One real, citable unit of indexed knowledge - a Markdown
    heading-scoped section, or one whole JSON file (a manifest or
    contract schema is never usefully split mid-object)."""

    source: str
    heading: str
    text: str
    kind: str  # "markdown" or "json" - what a caller can honestly cite this as


@dataclass(frozen=True)
class TfidfIndex:
    chunks: tuple[KnowledgeChunk, ...]
    idf: dict[str, float]
    chunk_vectors: tuple[dict[str, float], ...]


def _term_frequencies(tokens: list[str]) -> dict[str, float]:
    counts = Counter(tokens)
    total = sum(counts.values())
    if total == 0:
        return {}
    return {term: count / total for term, count in counts.items()}


def build_index(chunks: list[KnowledgeChunk]) -> TfidfIndex:
    chunk_tokens = [tokenize(chunk.text) for chunk in chunks]
    doc_count = len(chunks)

    doc_freq: Counter[str] = Counter()
    for tokens in chunk_tokens:
        doc_freq.update(set(tokens))

    idf = {
        term: math.log((1 + doc_count) / (1 + freq)) + 1.0
        for term, freq in doc_freq.items()
    }

    chunk_vectors: list[dict[str, float]] = []
    for tokens in chunk_tokens:
        tf = _term_frequencies(tokens)
        chunk_vectors.append({term: weight * idf[term] for term, weight in tf.items()})

    return TfidfIndex(chunks=tuple(chunks), idf=idf, chunk_vectors=tuple(chunk_vectors))


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    # Sorted for the same real reason DOCS-QA's own _cosine_similarity
    # sorts: CPython set iteration order depends on the process's own
    # randomized string hash seed, and float addition is not
    # associative - sorting removes that as a source of a
    # process-dependent score.
    shared = sorted(a.keys() & b.keys())
    dot = sum(a[term] * b[term] for term in shared)
    norm_a = math.sqrt(sum(weight * weight for weight in a.values()))
    norm_b = math.sqrt(sum(weight * weight for weight in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass(frozen=True)
class SearchResult:
    chunk: KnowledgeChunk
    score: float


def search(index: TfidfIndex, query: str, *, top_k: int = 5) -> list[SearchResult]:
    if top_k < 0:
        raise ValueError(f"top_k must be >= 0, got {top_k}")

    query_tf = _term_frequencies(tokenize(query))
    query_vector = {
        term: weight * index.idf[term] for term, weight in query_tf.items() if term in index.idf
    }

    results = [
        SearchResult(chunk=chunk, score=_cosine_similarity(query_vector, vector))
        for chunk, vector in zip(index.chunks, index.chunk_vectors)
    ]
    results = [result for result in results if result.score > 0.0]
    results.sort(key=lambda result: result.score, reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# Ingestion - bounded, allow-listed-root-scoped, real files only.
# ---------------------------------------------------------------------------

ALLOWED_SUFFIXES = frozenset({".md", ".markdown", ".json"})
MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
# Real bound on the walk itself, independent of how large an allow-listed
# root happens to be - "never trained blindly on the whole disk" holds
# even for a root an operator configured, not just for paths a model
# might request. A root with more files than this is a real
# misconfiguration to fix, not something to silently truncate forever;
# `ingest_source_directory` reports how many it actually indexed.
MAX_INDEXED_FILES = 500

_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def _canonical_source(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _ingest_markdown_text(text: str, *, source: str) -> list[KnowledgeChunk]:
    """Same real heading-scoped chunking DOCS-QA's own
    ingest_markdown_text uses (including the fenced-code-block
    guard, so a `# comment` inside a ```sh block is never read as a
    real heading)."""
    chunks: list[KnowledgeChunk] = []
    heading = ""
    body_lines: list[str] = []
    fence: str | None = None

    def flush() -> None:
        body = "\n".join(body_lines).strip()
        if body:
            chunks.append(KnowledgeChunk(source=source, heading=heading, text=body, kind="markdown"))

    for line in text.splitlines():
        stripped = line.strip()
        fence_match = _FENCE_RE.match(stripped)
        if fence is not None:
            body_lines.append(line)
            if fence_match and fence_match.group(1)[0] == fence[0] and len(fence_match.group(1)) >= len(fence):
                fence = None
            continue
        if fence_match:
            fence = fence_match.group(1)
            body_lines.append(line)
        elif stripped.startswith("#"):
            flush()
            heading = stripped.lstrip("#").strip()
            body_lines = []
        else:
            body_lines.append(line)
    flush()
    return chunks


def _ingest_json_text(text: str, *, source: str) -> list[KnowledgeChunk]:
    """One whole JSON file (a manifest, a contract schema) becomes
    exactly one real chunk - re-serialized pretty-printed so its own
    real structure stays searchable/citable, never truncated mid-object.
    Malformed JSON is skipped (not indexed) rather than indexing raw,
    possibly-corrupt bytes as if they were real structured data."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    pretty = json.dumps(parsed, indent=2, ensure_ascii=False, sort_keys=True)
    return [KnowledgeChunk(source=source, heading="", text=pretty, kind="json")]


@dataclass(frozen=True)
class IngestResult:
    chunks: tuple[KnowledgeChunk, ...]
    indexed_sources: tuple[str, ...]
    skipped_sources: tuple[str, ...]  # too large, disallowed extension, or unreadable
    truncated: bool  # True if MAX_INDEXED_FILES cut the walk short


def ingest_source_directory(root: Path) -> IngestResult:
    """Walks `root` (already resolved via the allow-list -
    `resolve_knowledge_source`, never a raw caller-supplied path) for
    real `.md`/`.markdown`/`.json` files, bounded by MAX_INDEXED_FILES
    and MAX_DOCUMENT_BYTES per file. Deterministic order (sorted), so
    which files get indexed first (and therefore which get dropped once
    MAX_INDEXED_FILES is reached) never depends on filesystem walk
    order."""
    if not root.is_dir():
        return IngestResult(chunks=(), indexed_sources=(), skipped_sources=(), truncated=False)

    candidates = sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix in ALLOWED_SUFFIXES),
        key=lambda p: p.as_posix(),
    )
    truncated = len(candidates) > MAX_INDEXED_FILES
    candidates = candidates[:MAX_INDEXED_FILES]

    all_chunks: list[KnowledgeChunk] = []
    indexed: list[str] = []
    skipped: list[str] = []
    for path in candidates:
        source = _canonical_source(path, root)
        try:
            if path.stat().st_size > MAX_DOCUMENT_BYTES:
                skipped.append(source)
                continue
            text = path.read_text(encoding="utf-8")
        except OSError:
            skipped.append(source)
            continue
        if path.suffix == ".json":
            chunks = _ingest_json_text(text, source=source)
        else:
            chunks = _ingest_markdown_text(text, source=source)
        if chunks:
            all_chunks.extend(chunks)
            indexed.append(source)
        else:
            skipped.append(source)

    return IngestResult(
        chunks=tuple(all_chunks),
        indexed_sources=tuple(indexed),
        skipped_sources=tuple(skipped),
        truncated=truncated,
    )
