"""Atomic JSON persistence of the full single-user Session to disk."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from llm.base import Message

STATE_PATH: Path = Path(__file__).parent / ".session" / "state.json"


def save_session(session) -> None:
    state = {
        "stack": session._stack,
        "idx": session._idx,
        "transcript": [m.to_dict() for m in session.transcript],
        "pending": session.pending,
        "speech_name": session.speech_name,
        "wavs": {k: base64.b64encode(v).decode("ascii") for k, v in session.wavs.items()},
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE_PATH)        # atomic on same filesystem


def load_session(session) -> bool:
    try:
        raw = STATE_PATH.read_text(encoding="utf-8")
        state = json.loads(raw)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    try:
        session._stack = state["stack"]
        session._idx = state["idx"]
        session.transcript = [Message.from_dict(m) for m in state.get("transcript", [])]
        session.pending = state.get("pending")
        session.speech_name = state.get("speech_name", "speech_export.json")
        session.wavs = {k: base64.b64decode(v) for k, v in state.get("wavs", {}).items()}
    except (KeyError, TypeError, ValueError):
        return False
    return True
