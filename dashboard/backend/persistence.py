"""Per-session snapshot persistence (save-slots model)."""
from __future__ import annotations

import base64
import json
import os
import re
import time
import uuid
from pathlib import Path

from llm.base import Message

_BASE = Path(__file__).parent
SESSIONS_DIR: Path = _BASE / ".sessions"
ACTIVE_PATH: Path = SESSIONS_DIR / "active"  # backward-compat; unused by new code
LEGACY_PATH: Path = _BASE / ".session" / "state.json"


def _safe_owner(owner: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", owner or "_legacy")


def _active_path(owner: str) -> Path:
    return SESSIONS_DIR / f"active.{_safe_owner(owner)}"


def _snapshot(session) -> dict:
    return {
        "id": session.id, "name": session.name,
        "owner": session.owner,
        "created": session.created, "updated": time.time(),
        "usage": session.usage,
        "stack": session._stack, "idx": session._idx,
        "transcript": [m.to_dict() for m in session.transcript],
        "pending": session.pending,
        "speech_name": session.speech_name,
        "wavs": {k: base64.b64encode(v).decode("ascii") for k, v in session.wavs.items()},
    }


def _restore(session, state: dict) -> None:
    session.id = state.get("id")
    session.name = state.get("name", "New session")
    session.owner = state.get("owner", "_legacy")
    session.created = state.get("created", time.time())
    session.updated = state.get("updated", time.time())
    session.usage = state.get("usage") or {"input_tokens": 0, "output_tokens": 0, "turns": 0, "model": None}
    session._stack = state["stack"]
    session._idx = state["idx"]
    session.transcript = [Message.from_dict(m) for m in state.get("transcript", [])]
    session.pending = state.get("pending")
    session.speech_name = state.get("speech_name", "speech_export.json")
    session.wavs = {k: base64.b64decode(v) for k, v in state.get("wavs", {}).items()}


def save_session(session) -> None:
    if not session.id:
        return
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / f"{session.id}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_snapshot(session), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def list_sessions(owner: str | None = None) -> list[dict]:
    if not SESSIONS_DIR.exists():
        return []
    out = []
    for p in SESSIONS_DIR.glob("*.json"):
        try:
            st = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if owner is not None and st.get("owner", "_legacy") != owner:
            continue
        stack = st.get("stack") or []
        out.append({"id": st.get("id"), "name": st.get("name", "Session"),
                    "updated": st.get("updated", 0),
                    "has_summary": bool(stack),
                    "usage": st.get("usage") or {"input_tokens": 0, "output_tokens": 0, "turns": 0, "model": None}})
    out.sort(key=lambda e: e["updated"], reverse=True)
    return out


def load_session(session, sid: str | None = None, owner: str | None = None) -> bool:
    sid = sid or (read_active(owner) if owner is not None else read_active(session.owner))
    if not sid:
        return False
    try:
        state = json.loads((SESSIONS_DIR / f"{sid}.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    if owner is not None and state.get("owner", "_legacy") != owner:
        return False
    try:
        _restore(session, state)
    except (KeyError, TypeError, ValueError):
        return False
    return True


def delete_session(sid: str, owner: str | None = None) -> None:
    if owner is not None:
        try:
            st = json.loads((SESSIONS_DIR / f"{sid}.json").read_text(encoding="utf-8"))
            if st.get("owner", "_legacy") != owner:
                return
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
    (SESSIONS_DIR / f"{sid}.json").unlink(missing_ok=True)


def read_active(owner: str) -> str | None:
    try:
        return _active_path(owner).read_text(encoding="utf-8").strip() or None
    except (FileNotFoundError, OSError):
        return None


def write_active(owner: str, sid: str) -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _active_path(owner).write_text(sid, encoding="utf-8")


def migrate_legacy(session) -> bool:
    """One-time: fold a legacy .session/state.json into a snapshot."""
    if list_sessions():
        return False
    try:
        state = json.loads(LEGACY_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    _restore(session, state)
    session.id = uuid.uuid4().hex
    session.name = "Imported session"
    session.owner = "_legacy"
    save_session(session)
    write_active("_legacy", session.id)
    return True
