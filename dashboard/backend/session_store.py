"""Save-slots session store, scoped to one owner (client)."""
from __future__ import annotations

import uuid

import persistence
from session import Session


class SessionStore:
    def __init__(self, owner: str = "_legacy") -> None:
        self.owner = owner
        self._active = Session()
        self._active.owner = owner

    def active(self) -> Session:
        return self._active

    def new(self, name: str = "New session") -> Session:
        self._active.reset()
        self._active.id = uuid.uuid4().hex
        self._active.owner = self.owner
        self._active.name = name
        self._active.usage = {"input_tokens": 0, "output_tokens": 0, "turns": 0, "model": None}
        persistence.save_session(self._active)
        persistence.write_active(self.owner, self._active.id)
        return self._active

    def activate(self, sid: str) -> bool:
        if not persistence.load_session(self._active, sid, owner=self.owner):
            return False
        persistence.write_active(self.owner, sid)
        return True

    def rename(self, sid: str, name: str) -> bool:
        if self._active.id == sid:
            self._active.name = name
            persistence.save_session(self._active)
            return True
        tmp = Session()
        tmp.owner = self.owner
        if not persistence.load_session(tmp, sid, owner=self.owner):
            return False
        tmp.name = name
        persistence.save_session(tmp)
        return True

    def delete(self, sid: str) -> None:
        persistence.delete_session(sid, owner=self.owner)
        if self._active.id == sid:
            remaining = persistence.list_sessions(self.owner)
            if remaining:
                self.activate(remaining[0]["id"])
            else:
                self._active.id = None
                self._active.reset()
                persistence._active_path(self.owner).unlink(missing_ok=True)

    def list(self) -> list[dict]:
        return persistence.list_sessions(self.owner)

    def boot(self) -> None:
        if persistence.load_session(self._active, persistence.read_active(self.owner), owner=self.owner):
            return
        if self.owner == "_legacy" and persistence.migrate_legacy(self._active):
            return
        # else: empty active object, no id (landing screen)
