"""Per-client registry of SessionStores (in-process multi-tenant)."""
from __future__ import annotations

import threading

from session_store import SessionStore


class Registry:
    def __init__(self) -> None:
        self._stores: dict[str, SessionStore] = {}
        self._lock = threading.Lock()

    def store(self, cid: str) -> SessionStore:
        with self._lock:
            s = self._stores.get(cid)
            if s is None:
                s = SessionStore(owner=cid)
                s.boot()
                self._stores[cid] = s
            return s

    def reset(self) -> None:
        with self._lock:
            self._stores.clear()


REGISTRY = Registry()
