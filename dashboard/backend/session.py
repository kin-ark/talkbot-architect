"""In-memory single-user session with an undo/redo version stack."""
from __future__ import annotations

import copy

from llm.base import Message


class Session:
    def __init__(self) -> None:
        self._stack: list[dict] = []
        self._idx: int = -1
        self.transcript: list[Message] = []
        self.pending: dict | None = None

    def load(self, data: dict) -> None:
        self._stack = [copy.deepcopy(data)]
        self._idx = 0
        self.transcript = []
        self.pending = None

    def current(self) -> dict:
        return self._stack[self._idx]

    def apply(self, proposed: dict) -> None:
        # Truncate any redo tail, push new version.
        self._stack = self._stack[: self._idx + 1]
        self._stack.append(copy.deepcopy(proposed))
        self._idx = len(self._stack) - 1
        self.pending = None

    def can_undo(self) -> bool:
        return self._idx > 0

    def can_redo(self) -> bool:
        return self._idx < len(self._stack) - 1

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        self._idx -= 1
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        self._idx += 1
        return True
