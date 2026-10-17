# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/escalation/outbox.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""A local queue of escalations that survives a network outage.

An escalation (a maintenance proposal with its evidence) is written to disk
first and marked sent only after the receiver confirmed it. Nothing is lost
when the link is down, nothing is sent twice after a restart, and every
entry keeps its own id so a resend is recognisable. Files are written
durably and atomically (temporary file, flushed to disk, then renamed), so
a power cut leaves either the whole entry or none of it. An entry that
cannot be read back is moved to `corrupt/` and skipped instead of
blocking every escalation queued after it.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")


@dataclass(frozen=True)
class QueuedEscalation:
    escalation_id: str
    payload: dict[str, Any]


class EscalationOutbox:
    def __init__(self, directory: Path) -> None:
        self._pending = directory / "pending"
        self._sent = directory / "sent"
        self._corrupt = directory / "corrupt"
        self._pending.mkdir(parents=True, exist_ok=True)
        self._sent.mkdir(parents=True, exist_ok=True)

    def _path(self, folder: Path, escalation_id: str) -> Path:
        if not _ID_RE.match(escalation_id):
            raise ValueError(f"unsafe escalation id: {escalation_id!r}")
        return folder / f"{escalation_id}.json"

    def enqueue(self, escalation_id: str, payload: dict[str, Any]) -> None:
        """Queue an escalation. Queueing the same id again is a no-op, so a retry cannot duplicate it."""
        target = self._path(self._pending, escalation_id)
        if target.exists() or self._path(self._sent, escalation_id).exists():
            return
        handle, temporary = tempfile.mkstemp(dir=self._pending, suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except BaseException:
            # A payload that cannot be serialised (or a full disk) must not
            # leave a half-written temporary file behind in the queue.
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        self._sync_directory(self._pending)

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        """Make the rename itself durable where the platform allows it
        (POSIX); Windows cannot open a directory, so it is skipped there."""
        try:
            descriptor = os.open(directory, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        except OSError:
            pass
        finally:
            os.close(descriptor)

    def _quarantine(self, path: Path) -> None:
        """Move an unreadable entry aside (never delete it: it may be the
        only record of an escalation a person still needs to see)."""
        self._corrupt.mkdir(parents=True, exist_ok=True)
        destination = self._corrupt / path.name
        suffix = 0
        while destination.exists():
            suffix += 1
            destination = self._corrupt / f"{path.stem}.{suffix}{path.suffix}"
        os.replace(path, destination)

    def pending(self) -> list[QueuedEscalation]:
        items = []
        for path in sorted(self._pending.glob("*.json")):
            if not _ID_RE.match(path.stem):
                self._quarantine(path)  # a name that mark_sent() would refuse could never leave the queue
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._quarantine(path)
                continue
            if not isinstance(payload, dict):
                self._quarantine(path)
                continue
            items.append(QueuedEscalation(path.stem, payload))
        return items

    def mark_sent(self, escalation_id: str) -> None:
        source = self._path(self._pending, escalation_id)
        if source.exists():
            os.replace(source, self._path(self._sent, escalation_id))

    def flush(self, send: Callable[[QueuedEscalation], bool]) -> int:
        """Try to send every pending item; stop at the first failure (the link is down).

        `send` returns True only when the receiver confirmed the item. Returns how many were sent.
        """
        sent = 0
        for item in self.pending():
            try:
                confirmed = send(item)
            except OSError:
                confirmed = False
            if not confirmed:
                break
            self.mark_sent(item.escalation_id)
            sent += 1
        return sent
