"""Save-slots session store: one active Session object, many disk snapshots."""
from __future__ import annotations

import uuid

import persistence
from session import Session


class SessionStore:
    def __init__(self) -> None:
        self._active = Session()

    def active(self) -> Session:
        return self._active

    def new(self, name: str = "New session") -> Session:
        self._active.reset()
        self._active.id = uuid.uuid4().hex
        self._active.name = name
        self._active.usage = {"input_tokens": 0, "output_tokens": 0, "turns": 0, "model": None}
        persistence.save_session(self._active)
        persistence.write_active(self._active.id)
        return self._active

    def activate(self, sid: str) -> bool:
        if not persistence.load_session(self._active, sid):
            return False
        persistence.write_active(sid)
        return True

    def rename(self, sid: str, name: str) -> bool:
        if self._active.id == sid:
            self._active.name = name
            persistence.save_session(self._active)
            return True
        # patch a non-active snapshot in place
        tmp = Session()
        if not persistence.load_session(tmp, sid):
            return False
        tmp.name = name
        persistence.save_session(tmp)
        return True

    def delete(self, sid: str) -> None:
        persistence.delete_session(sid)
        if self._active.id == sid:
            remaining = persistence.list_sessions()
            if remaining:
                self.activate(remaining[0]["id"])
            else:
                self._active.reset()
                self._active.id = None

    def list(self) -> list[dict]:
        return persistence.list_sessions()

    def boot(self) -> None:
        if persistence.load_session(self._active):      # active id on disk
            return
        if persistence.migrate_legacy(self._active):    # legacy → snapshot
            return
        # else: empty active object, no id (landing screen)
