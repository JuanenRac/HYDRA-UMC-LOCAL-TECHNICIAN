# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/knowledge/index.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
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
Nothing is trusted to a cache that could be stale: a file is read and chunked again whenever its modification time or size changed,
and the index is rebuilt whenever any file of the root appeared, vanished or changed (`cached_index`). The cache lives in this
process only (the read-only API keeps one, a one-shot command starts empty) and holds at most `MAX_CACHED_FILES` files. When the
configuration turns it on (`configure_persistence`), the chunks of every file are also kept on disk, versioned (`STORE_FORMAT`), and
a later process reads again only the files whose modification time or size changed; a store that is damaged or of another format
is ignored and made again, never trusted.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# Same real accented-Latin + CJK-bigram tokenizer HYDRA-UMC-DOCS-QA's own
# index.py already established and tested - this technician's
# own docs are written in the same 8 languages as every other repo in
# this ecosystem.
_LATIN_TOKEN_RE = re.compile(r"[a-z0-9À-ÖØ-öø-ɏ]+")
_CJK_RUN_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]+")  # kana, extension A, unified ideographs, compatibility ideographs
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
        for chunk, vector in zip(index.chunks, index.chunk_vectors, strict=True)
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

# Directories never worth indexing (and often enormous), pruned during the walk,
# and files that are generated data rather than documentation.
EXCLUDED_DIR_NAMES = frozenset({".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox"})
EXCLUDED_FILE_NAMES = frozenset({"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock"})
# Total size of the files one search may read; the per-file limit alone allowed ~2 GiB.
MAX_TOTAL_BYTES = 64 * 1024 * 1024

_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def _bounded_candidates(root: Path) -> tuple[list[Path], bool]:
    """The files to index, in deterministic order, found WITHOUT walking the
    whole tree first: excluded directories are pruned, symbolic links to
    directories are not followed, and the walk stops once the file-count or
    total-size bound is exceeded (reported as truncated)."""
    found: list[Path] = []
    total_bytes = 0
    truncated = False
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIR_NAMES)
        for name in sorted(filenames):
            path = Path(current, name)
            if name in EXCLUDED_FILE_NAMES or path.suffix not in ALLOWED_SUFFIXES or not path.is_file():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if len(found) >= MAX_INDEXED_FILES or total_bytes + min(size, MAX_DOCUMENT_BYTES) > MAX_TOTAL_BYTES:
                truncated = True
                break
            found.append(path)
            total_bytes += min(size, MAX_DOCUMENT_BYTES)
        if truncated:
            break
    return sorted(found, key=lambda p: p.as_posix()), truncated


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
    # What the walk saw: (source, modification time in ns, size) of every candidate, and the truncation. Equal fingerprints mean the
    # same files in the same state, so an index built from them is still the index of the root.
    fingerprint: tuple[object, ...] = ()


# Files already read and chunked, by (resolved root, source): (mtime_ns, size, chunks or None when the file gave nothing / was skipped, why).
MAX_CACHED_FILES = 4096
_CACHE_LOCK = threading.Lock()
_FILE_CACHE: dict[tuple[str, str], tuple[int, int, tuple[KnowledgeChunk, ...], str]] = {}
_INDEX_CACHE: dict[str, tuple[tuple[object, ...], IngestResult, TfidfIndex]] = {}


# The on-disk copy of the chunks of each file (closed unless configured): format 1 = {"format", "root", "files": {source: [mtime_ns, size, [chunk...]]}}.
STORE_FORMAT = 1
_STORE_DIRECTORY: Path | None = None
_STORE_MAX_FILES = MAX_CACHED_FILES
_STORE_LOADED: set[str] = set()
_STORE_SOURCES: dict[str, set[str]] = {}


def configure_persistence(directory: str | os.PathLike[str] | None, *, max_files: int = MAX_CACHED_FILES) -> None:
    """Keeps (a directory) or stops keeping (None) the chunks of the indexed files on disk between runs."""
    global _STORE_DIRECTORY, _STORE_MAX_FILES
    with _CACHE_LOCK:
        _STORE_DIRECTORY = Path(directory) if directory else None
        _STORE_MAX_FILES = max(1, int(max_files))
        _STORE_LOADED.clear()
        _STORE_SOURCES.clear()


def _store_path(root_key: str) -> Path | None:
    if _STORE_DIRECTORY is None:
        return None
    return _STORE_DIRECTORY / f"knowledge-{hashlib.sha256(root_key.encode('utf-8')).hexdigest()[:32]}.json"


def _load_store(root_key: str) -> None:
    """Fills the file cache of a root from its stored copy, once per process; anything that is not the exact documented shape is dropped."""
    path = _store_path(root_key)
    if path is None or root_key in _STORE_LOADED:
        return
    _STORE_LOADED.add(root_key)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("format") != STORE_FORMAT or raw.get("root") != root_key or not isinstance(raw.get("files"), dict):
            return
        loaded: dict[tuple[str, str], tuple[int, int, tuple[KnowledgeChunk, ...], str]] = {}
        for source, entry in raw["files"].items():
            mtime, size, chunks = entry
            if not (isinstance(source, str) and isinstance(mtime, int) and isinstance(size, int) and isinstance(chunks, list)):
                return
            loaded[(root_key, source)] = (
                mtime, size,
                tuple(KnowledgeChunk(source=c["source"], heading=c["heading"], text=c["text"], kind=c["kind"]) for c in chunks),
                "",
            )
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return
    _STORE_SOURCES[root_key] = {key[1] for key in loaded}
    for key, value in loaded.items():
        if len(_FILE_CACHE) < MAX_CACHED_FILES:
            _FILE_CACHE.setdefault(key, value)


def _save_store(root_key: str, fingerprint: list[object]) -> None:
    """Writes the chunks of the files the last walk saw (a vanished file leaves the store); a failure to write never breaks a search."""
    path = _store_path(root_key)
    if path is None:
        return
    files: dict[str, list[object]] = {}
    for source, mtime, size in (item for item in fingerprint if isinstance(item, tuple)):
        entry = _FILE_CACHE.get((root_key, source))
        if entry is None or (entry[0], entry[1]) != (mtime, size) or len(files) >= _STORE_MAX_FILES:
            continue
        files[source] = [mtime, size, [{"source": c.source, "heading": c.heading, "text": c.text, "kind": c.kind} for c in entry[2]]]
    payload = json.dumps({"format": STORE_FORMAT, "root": root_key, "files": files}, ensure_ascii=False, sort_keys=True)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".knowledge-", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                out.write(payload)
            os.replace(temporary, path)
        except OSError:
            Path(temporary).unlink(missing_ok=True)
    except OSError:
        return


def clear_caches() -> None:
    with _CACHE_LOCK:
        _FILE_CACHE.clear()
        _INDEX_CACHE.clear()
        _STORE_LOADED.clear()
        _STORE_SOURCES.clear()


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

    candidates, truncated = _bounded_candidates(root)
    root_key = str(root.resolve())
    with _CACHE_LOCK:
        _load_store(root_key)
    changed = False

    all_chunks: list[KnowledgeChunk] = []
    indexed: list[str] = []
    skipped: list[str] = []
    fingerprint: list[object] = []
    for path in candidates:
        try:
            source = _canonical_source(path, root)
        except (ValueError, OSError):
            # A symlink inside the allow-listed root that points outside
            # it: the allow-list is the root, so what it points at is not
            # part of the knowledge source - skipped by name, never read,
            # and never allowed to abort the whole search.
            skipped.append(path.relative_to(root).as_posix())
            continue
        try:
            stat = path.stat()
        except OSError:
            skipped.append(source)
            continue
        signature = (stat.st_mtime_ns, stat.st_size)
        fingerprint.append((source, *signature))
        with _CACHE_LOCK:
            cached = _FILE_CACHE.get((root_key, source))
        if cached is not None and (cached[0], cached[1]) == signature:
            chunks = cached[2]
        else:
            try:
                if stat.st_size > MAX_DOCUMENT_BYTES:
                    skipped.append(source)
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                # One file that is not valid UTF-8 (a Latin-1 export, a binary
                # saved as .md) must not take the other 499 down with it.
                skipped.append(source)
                continue
            if path.suffix == ".json":
                chunks = tuple(_ingest_json_text(text, source=source))
            else:
                chunks = tuple(_ingest_markdown_text(text, source=source))
            with _CACHE_LOCK:
                if len(_FILE_CACHE) >= MAX_CACHED_FILES and (root_key, source) not in _FILE_CACHE:
                    _FILE_CACHE.pop(next(iter(_FILE_CACHE)))  # the oldest entry goes
                _FILE_CACHE[(root_key, source)] = (signature[0], signature[1], chunks, "")
            changed = True
        if chunks:
            all_chunks.extend(chunks)
            indexed.append(source)
        else:
            skipped.append(source)

    if _STORE_DIRECTORY is not None:
        with _CACHE_LOCK:
            seen = {item[0] for item in fingerprint if isinstance(item, tuple) and (root_key, item[0]) in _FILE_CACHE}
            if changed or seen != _STORE_SOURCES.get(root_key, set()):
                _save_store(root_key, fingerprint)
                _STORE_SOURCES[root_key] = seen

    return IngestResult(
        chunks=tuple(all_chunks),
        indexed_sources=tuple(indexed),
        skipped_sources=tuple(skipped),
        truncated=truncated,
        fingerprint=(*fingerprint, truncated),
    )


def cached_index(root: Path) -> tuple[IngestResult, TfidfIndex]:
    """What a search needs: the ingested root and its index. The index of a root whose files are all as they were at the last call
    is returned as it is; any file that appeared, vanished or changed makes it new."""
    ingested = ingest_source_directory(root)
    if not ingested.fingerprint:
        return ingested, build_index(list(ingested.chunks))
    key = str(root.resolve())
    with _CACHE_LOCK:
        held = _INDEX_CACHE.get(key)
    if held is not None and held[0] == ingested.fingerprint:
        return held[1], held[2]
    index = build_index(list(ingested.chunks))
    with _CACHE_LOCK:
        if len(_INDEX_CACHE) >= 64 and key not in _INDEX_CACHE:
            _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
        _INDEX_CACHE[key] = (ingested.fingerprint, ingested, index)
    return ingested, index
