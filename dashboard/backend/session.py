"""In-memory single-user session with an undo/redo version stack."""
from __future__ import annotations

import copy
import threading
import time

from llm.base import Message


class Session:
    def __init__(self) -> None:
        self.id: str | None = None
        self.name: str = "New session"
        self.owner: str = "_legacy"
        self.created: float = time.time()
        self.updated: float = time.time()
        self.usage: dict = {"input_tokens": 0, "output_tokens": 0, "turns": 0, "model": None}
        self._stack: list[dict] = []
        self._idx: int = -1
        self.transcript: list[Message] = []
        self.pending: dict | None = None
        self.speech_name: str = "speech_export.json"
        self.wavs: dict[str, bytes] = {}
        self.is_component: bool = False
        self.component_base: dict | None = None
        self.cancel_requested: bool = False
        self.attachment: dict | None = None
        self.images: list = []
        self._lock = threading.Lock()

    def _autosave(self) -> None:
        try:
            import persistence
            persistence.save_session(self)
        except Exception:
            pass        # best-effort; never break an API call on a write error

    def load(
        self,
        data: dict,
        *,
        speech_name: str = "speech_export.json",
        wavs: dict[str, bytes] | None = None,
        is_component: bool = False,
        component_base: dict | None = None,
    ) -> None:
        # Keep id/name (slot identity); refresh updated timestamp
        self.updated = time.time()
        self._stack = [copy.deepcopy(data)]
        self._idx = 0
        self.transcript = []
        self.pending = None
        self.attachment = None
        self.images = []
        self.speech_name = speech_name
        self.wavs = wavs if wavs is not None else {}
        self.is_component = is_component
        self.component_base = copy.deepcopy(component_base) if component_base is not None else None
        self._autosave()

    def reset(self) -> None:
        """Drop the loaded dialogue + transcript so the app returns to landing."""
        # Keep id/name (same slot being emptied); zero usage
        self.usage = {"input_tokens": 0, "output_tokens": 0, "turns": 0, "model": None}
        self._stack = []
        self._idx = -1
        self.transcript = []
        self.pending = None
        self.is_component = False
        self.component_base = None
        self.cancel_requested = False
        self._autosave()

    def current(self) -> dict:
        return self._stack[self._idx]

    def apply(self, proposed: dict) -> None:
        # Truncate any redo tail, push new version.
        self._stack = self._stack[: self._idx + 1]
        self._stack.append(copy.deepcopy(proposed))
        self._idx = len(self._stack) - 1
        self.pending = None
        self._autosave()

    def can_undo(self) -> bool:
        return self._idx > 0

    def can_redo(self) -> bool:
        return self._idx < len(self._stack) - 1

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        self._idx -= 1
        self._autosave()
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        self._idx += 1
        self._autosave()
        return True
