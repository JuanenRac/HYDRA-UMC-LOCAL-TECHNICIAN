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
atomically (temporary file, then rename).
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
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
        os.replace(temporary, target)

    def pending(self) -> list[QueuedEscalation]:
        items = []
        for path in sorted(self._pending.glob("*.json")):
            items.append(QueuedEscalation(path.stem, json.loads(path.read_text(encoding="utf-8"))))
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
