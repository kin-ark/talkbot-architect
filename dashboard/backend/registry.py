"""Per-client registry of SessionStores (in-process multi-tenant)."""
from __future__ import annotations

import os
import threading
from collections import OrderedDict

from session_store import SessionStore

# LRU cap so idle cookies don't accumulate stores forever. Session state is
# persisted to disk, so an evicted store reloads (via boot()) on next access.
_MAX_STORES = int(os.getenv("MAX_CLIENT_STORES", "500"))


class Registry:
    def __init__(self) -> None:
        self._stores: "OrderedDict[str, SessionStore]" = OrderedDict()
        self._lock = threading.Lock()

    def store(self, cid: str) -> SessionStore:
        with self._lock:
            s = self._stores.get(cid)
            if s is None:
                s = SessionStore(owner=cid)
                s.boot()
                self._stores[cid] = s
            else:
                self._stores.move_to_end(cid)       # mark most-recently-used
            while len(self._stores) > _MAX_STORES:
                self._stores.popitem(last=False)     # evict least-recently-used
            return s

    def reset(self) -> None:
        with self._lock:
            self._stores.clear()


REGISTRY = Registry()
