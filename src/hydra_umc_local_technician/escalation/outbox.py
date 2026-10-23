# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/escalation/outbox.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
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
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
# A temporary file older than this was left by a process that died between writing it and renaming it
# (kill -9, power cut). One younger than this may be being written right now by another process.
STALE_TEMPORARY_SECONDS = 600.0

# What enqueue() answers
QUEUED = "queued"
DUPLICATE = "duplicate"  # the same id with the same payload was already there: nothing to do
CONFLICT = "conflict"  # the same id with ANOTHER payload was already there: the first is kept, the second is set aside


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
        self.set_aside_stale_temporaries()

    def _path(self, folder: Path, escalation_id: str) -> Path:
        if not _ID_RE.match(escalation_id):
            raise ValueError(f"unsafe escalation id: {escalation_id!r}")
        return folder / f"{escalation_id}.json"

    def set_aside_stale_temporaries(self, now: float | None = None) -> int:
        """Move the `*.tmp` files a dead process left in `pending/` to `corrupt/` (never delete: a half-written
        escalation may be the only trace of one a person still has to see). Returns how many."""
        moved = 0
        current = time.time() if now is None else now
        for path in self._pending.glob("*.tmp"):
            try:
                age = current - path.stat().st_mtime
            except OSError:
                continue
            if age < STALE_TEMPORARY_SECONDS:
                continue
            try:
                self._quarantine(path)
            except OSError:
                continue
            moved += 1
        return moved

    def enqueue(self, escalation_id: str, payload: dict[str, Any]) -> str:
        """Queue an escalation and say what happened: QUEUED, DUPLICATE (same id, same payload: a retry cannot
        duplicate it) or CONFLICT (same id, another payload: the first is kept and the second is set aside in
        `corrupt/` for a person to see, instead of one silently replacing the other).

        The entry is created exclusively (a hard link of the finished temporary file), so two processes queueing
        the same id cannot both succeed."""
        target = self._path(self._pending, escalation_id)
        for existing in (target, self._path(self._sent, escalation_id)):
            if existing.exists():
                return self._answer_for_existing(existing, escalation_id, payload)
        handle, temporary = tempfile.mkstemp(dir=self._pending, suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, target)  # fails if the id appeared since the check above
            except FileExistsError:
                answer = self._answer_for_existing(target, escalation_id, payload)
                os.unlink(temporary)
                temporary = ""
                return answer
            except OSError:
                # a file system without hard links: the plain rename, without the exclusivity
                os.replace(temporary, target)
                temporary = ""
        except BaseException:
            # A payload that cannot be serialised (or a full disk) must not
            # leave a half-written temporary file behind in the queue.
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            raise
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        self._sync_directory(self._pending)
        return QUEUED

    def _answer_for_existing(self, existing: Path, escalation_id: str, payload: dict[str, Any]) -> str:
        try:
            same = json.loads(existing.read_text(encoding="utf-8")) == json.loads(json.dumps(payload, sort_keys=True))
        except (OSError, ValueError):
            same = False
        if same:
            return DUPLICATE
        self._corrupt.mkdir(parents=True, exist_ok=True)
        destination = self._corrupt / f"{escalation_id}.conflict.json"
        suffix = 0
        while destination.exists():
            suffix += 1
            destination = self._corrupt / f"{escalation_id}.conflict.{suffix}.json"
        destination.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return CONFLICT

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
        if not source.exists():
            return
        destination = self._path(self._sent, escalation_id)
        if destination.exists():
            # already recorded as sent (a crash between two steps, or a second queueing): the record of what was
            # sent stays as it is, and the pending copy leaves the queue without overwriting it
            self._quarantine(source)
            return
        os.replace(source, destination)

    def flush(self, send: Callable[[QueuedEscalation], bool]) -> int:
        """Try to send every pending item; stop at the first failure (the link is down).

        `send` returns True only when the receiver confirmed the item. Returns how many were sent.
        """
        sent = 0
        for item in self.pending():
            try:
                confirmed = send(item)
            except Exception:  # noqa: BLE001 - whatever the transport raised, nothing was confirmed: keep it queued
                confirmed = False
            if not confirmed:
                break
            self.mark_sent(item.escalation_id)
            sent += 1
        return sent
