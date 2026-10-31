# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/orchestrator/audit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""An append-only audit journal of every tool request and what became of it.

One JSON object per line, written before a tool runs ("request") and after ("result" or "refused"), so a
request that crashes the process still leaves its first line behind. Every line carries `prev`, the SHA-256 of
the line before it, so a line removed or edited afterwards breaks the chain and `verify()` says where. When the
file reaches `max_bytes` it is rotated (`audit.jsonl` -> `audit.jsonl.1` -> ...) and the chain continues in the
new file; `backups` rotated files are kept.

Everything written is redacted first (arguments, actor and reason go through the shared secret redaction). The
journal is opt-in: a deployment turns it on with `--audit-log PATH` or `HYDRA_UMC_LOCAL_TECHNICIAN_AUDIT_LOG`, or
the `auditLog` key of the configuration file. When it is on, a request whose first line cannot be written is not
run: nothing executes unrecorded.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..knowledge.redaction import redact_json

ENVIRONMENT_VARIABLE = "HYDRA_UMC_LOCAL_TECHNICIAN_AUDIT_LOG"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUPS = 5
GENESIS = "0" * 64


class AuditWriteError(OSError):
    """The journal could not take a line."""


def _digest(line: bytes) -> str:
    return hashlib.sha256(line).hexdigest()


class AuditLog:
    def __init__(self, path: str | Path, *, max_bytes: int = DEFAULT_MAX_BYTES, backups: int = DEFAULT_BACKUPS) -> None:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1024:
            raise ValueError("max_bytes must be an integer of at least 1024")
        if not isinstance(backups, int) or isinstance(backups, bool) or not 0 <= backups <= 100:
            raise ValueError("backups must be an integer between 0 and 100")
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.backups = backups
        self._lock = threading.Lock()
        self._previous: str | None = None

    # ------------------------------------------------------------------ writing
    def _last_digest(self) -> str:
        """The digest of the last line on disk (this file, else the newest rotated one), or the genesis value."""
        for candidate in (self.path, Path(f"{self.path}.1")):
            try:
                data = candidate.read_bytes()
            except OSError:
                continue
            lines = [line for line in data.split(b"\n") if line]
            if lines:
                return _digest(lines[-1])
        return GENESIS

    def _rotate(self) -> None:
        if self.backups == 0:
            self.path.unlink(missing_ok=True)
            return
        oldest = Path(f"{self.path}.{self.backups}")
        oldest.unlink(missing_ok=True)
        for index in range(self.backups - 1, 0, -1):
            source = Path(f"{self.path}.{index}")
            if source.exists():
                source.replace(Path(f"{self.path}.{index + 1}"))
        self.path.replace(Path(f"{self.path}.1"))

    def record(self, event: dict[str, Any]) -> None:
        """Append one redacted line. Raises AuditWriteError when it cannot be written."""
        body: Any = redact_json(event)
        body["time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self._previous is None:
                    self._previous = self._last_digest()
                body["prev"] = self._previous
                line = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                if self.path.exists() and self.path.stat().st_size + len(line) + 1 > self.max_bytes:
                    self._rotate()
                descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o640)
                try:
                    os.write(descriptor, line + b"\n")
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                self._previous = _digest(line)
            except OSError as error:
                self._previous = None
                raise AuditWriteError(f"audit journal {self.path} is not writable: {error}") from error

    def record_request(self, request: Any) -> None:
        self.record({
            "event": "request", "requestId": request.request_id, "tool": request.tool,
            "arguments": request.arguments, "riskLevel": request.risk_level.wire_name,
            "actor": request.actor, "reason": request.reason,
        })

    def record_outcome(self, request: Any, event: str, **fields: Any) -> None:
        """The closing line. A failure here is not allowed to hide a result that already exists."""
        try:
            self.record({"event": event, "requestId": request.request_id, "tool": request.tool, **fields})
        except AuditWriteError:
            pass

    # ------------------------------------------------------------------ reading
    def files(self) -> list[Path]:
        """Oldest first: the rotated files, then the current one."""
        rotated = []
        for index in range(self.backups, 0, -1):
            candidate = Path(f"{self.path}.{index}")
            if candidate.exists():
                rotated.append(candidate)
        return rotated + ([self.path] if self.path.exists() else [])

    def verify(self) -> tuple[bool, str]:
        """(True, summary) when the chain is unbroken from the oldest line kept; else (False, where it breaks)."""
        previous: str | None = None
        count = 0
        for file in self.files():
            for number, line in enumerate(file.read_bytes().split(b"\n"), start=1):
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    return False, f"{file.name}:{number}: not valid JSON"
                if previous is not None and record.get("prev") != previous:
                    return False, f"{file.name}:{number}: the line before it was changed or removed"
                previous = _digest(line)
                count += 1
        return True, f"{count} line(s), chain intact"


def audit_log_from(path: str | None, environ: dict[str, str] | None = None, **options: Any) -> AuditLog | None:
    """The journal chosen by an explicit path, else the environment; None when neither is set."""
    chosen = path or (os.environ if environ is None else environ).get(ENVIRONMENT_VARIABLE, "").strip()
    return AuditLog(chosen, **options) if chosen else None
