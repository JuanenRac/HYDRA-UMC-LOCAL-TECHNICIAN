# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/webapi.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Fase 5: a local, read-only HTTP API and a single-page web UI over what the
technician has already produced.

It serves, never changes: the tool registry, the ToolResult / EvidenceBundle /
MaintenanceProposal files a data directory holds (what `tools call` and
`escalation evidence|propose` printed and an operator saved), the project
manifests under the configured ecosystem root, and the document index of the
allow-listed knowledge sources. It runs no tool, calls no model and writes
nothing: only GET is answered, every other method gets 405, and no handler
here opens a file for writing.

Safety properties, each covered by a test:

- loopback by default; any other address needs a bearer token of at least 24
  characters (compared in constant time), and the server refuses to start
  without one. On a loopback address a token is optional, but if one is given
  it is enforced, and a request whose Host header is not a loopback name is
  refused (DNS rebinding).
- an item is found by LISTING its directory and matching the id against the
  names found, never by joining a request path onto a directory, so `..`,
  encoded separators and absolute paths simply do not match anything.
- every JSON body, whatever its source, leaves through one function that
  applies the same redaction as the CLI (knowledge/redaction.py); document text
  is redacted too.
- bounded everywhere: a file over MAX_ITEM_BYTES is refused with 413, a list
  holds at most MAX_LIST_ITEMS entries, a document answer at most
  MAX_DOC_CHARS characters, and the request line and headers are bounded by the
  standard library's own limits.
- the page has no external resource: scripts, styles and translations are
  served from this package under a Content-Security-Policy that allows only
  this origin.
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from . import __version__
from .knowledge.index import ingest_source_directory
from .knowledge.redaction import redact_json, redact_secrets
from .orchestrator.allowlist import OrchestratorConfig, UnknownAllowlistEntry
from .orchestrator.dispatch import ToolDispatchError, dispatch_tool_request
from .knowledge.trust import ToolCallRefused, build_tool_request_from_model_output
from .policy.tool_matrix import TOOL_MATRIX

MIN_TOKEN_LENGTH = 24
MAX_ITEM_BYTES = 1024 * 1024
MAX_LIST_ITEMS = 500
DEFAULT_PAGE_SIZE = 100
MAX_DOC_CHARS = 200_000
MAX_MANIFESTS = 300

LANGUAGES = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
WEBUI_DIR = Path(__file__).resolve().parent / "webui"

# the three stores a data directory may hold: URL name -> sub-directory
STORES = {"tool-results": "tool-results", "evidence": "evidence", "proposals": "proposals"}

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
_LOOPBACK_NAMES = {"127.0.0.1", "localhost", "::1"}

# the only files the page itself can fetch: URL path -> (file, content type)
_STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    **{f"/i18n/{code}.json": (f"i18n/{code}.json", "application/json; charset=utf-8") for code in LANGUAGES},
}

_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


class ApiConfigError(ValueError):
    """The API cannot be started with these settings."""


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_bind(host: str, token: str | None) -> None:
    """Loopback needs no token; anything else (including 0.0.0.0) needs a real one."""
    if token is not None and (not isinstance(token, str) or len(token) < MIN_TOKEN_LENGTH):
        raise ApiConfigError(f"the API token must be at least {MIN_TOKEN_LENGTH} characters")
    if not _is_loopback(host) and not token:
        raise ApiConfigError(
            f"binding to {host!r} (not a loopback address) requires a bearer token of at least {MIN_TOKEN_LENGTH} characters"
        )


class TechnicianServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        data_dir: Path,
        config: OrchestratorConfig,
        token: str | None = None,
    ) -> None:
        validate_bind(address[0], token)
        super().__init__(address, _Handler)
        self.data_dir = Path(data_dir)
        self.config = config
        self.token = token or None
        self.loopback = _is_loopback(address[0])


def _store_files(directory: Path) -> dict[str, Path]:
    """id -> file for the `*.json` files directly inside `directory`, found by listing."""
    found: dict[str, Path] = {}
    try:
        entries = sorted(directory.iterdir(), key=lambda p: p.name)
    except OSError:
        return found
    for entry in entries:
        if entry.suffix == ".json" and _ID_RE.match(entry.stem) and entry.is_file() and not entry.is_symlink():
            found.setdefault(entry.stem, entry)
    return found


def _read_json_file(path: Path) -> tuple[Any, str | None]:
    """(value, None) or (None, reason). A file over MAX_ITEM_BYTES is not read."""
    try:
        if path.stat().st_size > MAX_ITEM_BYTES:
            return None, "too_large"
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, ValueError):
        return None, "unreadable"


def _short(value: Any, limit: int = 160) -> str:
    text = value if isinstance(value, str) else ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summary(store: str, item_id: str, value: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": item_id}
    if not isinstance(value, dict):
        return entry
    if store == "tool-results":
        entry.update(status=_short(value.get("status")), timestamp=_short(value.get("timestamp")), requestId=_short(value.get("requestId")), evidence=_short(value.get("evidence")))
    elif store == "evidence":
        entry.update(date=_short(value.get("date")), impact=_short(value.get("impact")), checksum=_short(value.get("checksum")))
    else:
        entry.update(risk=_short(value.get("risk")), scope=_short(value.get("scope")), diagnosis=_short(value.get("diagnosis")))
    return entry


class _Handler(BaseHTTPRequestHandler):
    server: TechnicianServer  # type: ignore[assignment]
    timeout = 15.0
    server_version = "HydraTechnician"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return  # request lines can carry ids and paths; keep the server quiet

    # -- plumbing ----------------------------------------------------------
    def _headers(self, status: int, content_type: str, length: int, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", _CSP)
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()

    def _send_json(self, status: int, payload: object, extra: dict[str, str] | None = None) -> None:
        """The one exit point of every JSON answer: it is redacted here."""
        body = json.dumps(redact_json(payload), ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body), extra)
        self.wfile.write(body)

    def _error(self, status: int, message: str, extra: dict[str, str] | None = None) -> None:
        self._send_json(status, {"error": message}, extra)

    def _authorized(self) -> bool:
        if self.server.token is None:
            return True
        scheme, _, presented = self.headers.get("Authorization", "").partition(" ")
        return scheme == "Bearer" and hmac.compare_digest(presented.encode("utf-8"), self.server.token.encode("utf-8"))

    def _host_ok(self) -> bool:
        """On a loopback bind, only a loopback Host header is served (DNS rebinding)."""
        if not self.server.loopback:
            return True
        host = (self.headers.get("Host") or "").strip().lower()
        if host.startswith("["):
            name = host[1:].split("]", 1)[0]
        else:
            name = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
        return name in _LOOPBACK_NAMES

    # -- methods -----------------------------------------------------------
    def _refuse(self) -> None:
        # Nothing is read from the request body: a write is never attempted.
        self._error(405, "this API is read-only: only GET is allowed", {"Allow": "GET"})
        self.close_connection = True

    do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = do_TRACE = do_CONNECT = _refuse  # noqa: N815

    def do_GET(self) -> None:  # noqa: N802
        if not self._host_ok():
            self._error(403, "this server answers only to loopback host names")
            return
        parts = urlsplit(self.path)
        path = parts.path
        if path in _STATIC:
            self._static(path)
            return
        if path == "/api/v1/health":
            self._send_json(200, {"status": "ok", "version": __version__, "readOnly": True})
            return
        if not path.startswith("/api/v1/"):
            self._error(404, "not found")
            return
        if not self._authorized():
            self._error(401, "a valid bearer token is required", {"WWW-Authenticate": "Bearer"})
            return
        segments = [unquote(segment) for segment in path[len("/api/v1/"):].split("/")]
        if any("/" in s or "\\" in s or "\0" in s for s in segments):
            self._error(404, "not found")
            return
        query = parse_qs(parts.query)
        try:
            self._route(segments, query)
        except Exception:  # noqa: BLE001 - one broken item must not stop the server
            self._error(500, "internal error")

    # -- static ------------------------------------------------------------
    def _static(self, path: str) -> None:
        name, content_type = _STATIC[path]
        try:
            body = (WEBUI_DIR / name).read_bytes()
        except OSError:
            self._error(404, "not found")
            return
        self._headers(200, content_type, len(body))
        self.wfile.write(body)

    # -- API ---------------------------------------------------------------
    def _route(self, segments: list[str], query: dict[str, list[str]]) -> None:
        head = segments[0]
        rest = segments[1:]
        if head == "tools" and not rest:
            tools = [
                {"name": name, "risk": d.risk_level.wire_name, "implemented": d.implemented, "description": d.description}
                for name, d in sorted(TOOL_MATRIX.items())
            ]
            self._send_json(200, {"tools": tools})
        elif head in STORES:
            self._store(head, rest, query)
        elif head == "manifests":
            self._manifests(rest)
        elif head == "docs":
            self._docs(rest, query)
        else:
            self._error(404, "not found")

    def _int_param(self, query: dict[str, list[str]], name: str, default: int, maximum: int) -> int:
        try:
            value = int(query.get(name, [str(default)])[0])
        except ValueError:
            return default
        return max(0, min(value, maximum))

    def _store(self, store: str, rest: list[str], query: dict[str, list[str]]) -> None:
        files = _store_files(self.server.data_dir / STORES[store])
        if not rest:
            limit = self._int_param(query, "limit", DEFAULT_PAGE_SIZE, MAX_LIST_ITEMS) or DEFAULT_PAGE_SIZE
            offset = self._int_param(query, "offset", 0, 10**9)
            names = list(files)[offset: offset + limit]
            items = []
            for item_id in names:
                value, problem = _read_json_file(files[item_id])
                entry = _summary(store, item_id, value)
                if problem:
                    entry["problem"] = problem
                items.append(entry)
            self._send_json(200, {"items": items, "total": len(files), "offset": offset, "limit": limit})
            return
        if len(rest) != 1 or not _ID_RE.match(rest[0]) or rest[0] not in files:
            self._error(404, "not found")
            return
        value, problem = _read_json_file(files[rest[0]])
        if problem == "too_large":
            self._error(413, f"this item is larger than {MAX_ITEM_BYTES} bytes and is not served")
        elif problem:
            self._error(422, "this item is not valid JSON")
        else:
            self._send_json(200, {"id": rest[0], "item": value})

    def _manifests(self, rest: list[str]) -> None:
        root = self.server.config.ecosystem_root
        if root is None:
            self._send_json(200, {"configured": False, "projects": []})
            return
        if rest:
            if len(rest) != 1:
                self._error(404, "not found")
                return
            self._manifest_one(rest[0])
            return
        projects = []
        try:
            children = sorted(p.name for p in Path(root).iterdir() if p.is_dir())
        except OSError:
            children = []
        for name in children:
            if len(projects) >= MAX_MANIFESTS:
                break
            result = self._manifest_result(name)
            if result is not None and result.get("status") == "ok" and result["output"].get("found"):
                projects.append(result["output"])
        self._send_json(200, {"configured": True, "projects": projects})

    def _manifest_result(self, project: str) -> dict[str, Any] | None:
        try:
            request = build_tool_request_from_model_output(
                request_id=f"web-{project}", tool="manifest.read", arguments={"project": project},
                actor="web", reason="read-only web view",
            )
            return dispatch_tool_request(request, self.server.config)
        except (ToolCallRefused, ToolDispatchError, UnknownAllowlistEntry):
            return None

    def _manifest_one(self, project: str) -> None:
        result = self._manifest_result(project)
        if result is None:
            self._error(404, "not found")
        else:
            self._send_json(200, result["output"])

    def _docs(self, rest: list[str], query: dict[str, list[str]]) -> None:
        sources = self.server.config.knowledge_sources
        if not rest:
            listing = []
            for name in sorted(sources):
                ingested = ingest_source_directory(sources[name])
                listing.append({
                    "name": name,
                    "documents": list(ingested.indexed_sources)[:MAX_LIST_ITEMS],
                    "total": len(ingested.indexed_sources),
                    "truncated": ingested.truncated or len(ingested.indexed_sources) > MAX_LIST_ITEMS,
                })
            self._send_json(200, {"sources": listing})
            return
        if len(rest) != 1 or rest[0] not in sources:
            self._error(404, "not found")
            return
        wanted = (query.get("path") or [""])[0]
        ingested = ingest_source_directory(sources[rest[0]])
        # only a path the index itself listed can be asked for: traversal has nothing to match
        if wanted not in set(ingested.indexed_sources):
            self._error(404, "not found")
            return
        remaining = MAX_DOC_CHARS
        chunks = []
        truncated = False
        for chunk in ingested.chunks:
            if chunk.source != wanted:
                continue
            text = chunk.text
            if len(text) > remaining:
                text, truncated = text[:remaining], True
            chunks.append({"heading": chunk.heading, "kind": chunk.kind, "text": redact_secrets(text)})
            remaining -= len(text)
            if remaining <= 0:
                truncated = True
                break
        self._send_json(200, {"source": rest[0], "path": wanted, "chunks": chunks, "truncated": truncated})


def read_api_token(token_file: str | None, environ: dict[str, str]) -> str | None:
    """The token comes from a file or the environment, never from the command line."""
    if token_file:
        text = Path(token_file).read_text(encoding="utf-8").strip()
        return text or None
    return environ.get("HYDRA_UMC_LOCAL_TECHNICIAN_TOKEN", "").strip() or None
