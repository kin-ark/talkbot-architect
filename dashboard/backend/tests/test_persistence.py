import persistence
from session import Session
from llm.base import Message, ToolCall


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")


def test_roundtrip_full_state(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    s = Session()
    s.id = "sess1"
    s.load({"BizSpeechComponent": [{"componentUuid": "c1"}]},
           speech_name="bot.json", wavs={"a.wav": b"\x00\x01RIFF"})
    s.id = "sess1"  # load() keeps id; re-assert in case
    s.apply({"BizSpeechComponent": [{"componentUuid": "c1", "edited": True}]})
    s.transcript.append(Message(role="assistant", content="hi",
                                tool_calls=[ToolCall("t1", "validate", {})]))
    s.pending = {"diff": "x", "proposed_data": {"k": 1}}
    persistence.save_session(s)

    s2 = Session()
    assert persistence.load_session(s2, "sess1") is True
    assert s2.current() == {"BizSpeechComponent": [{"componentUuid": "c1", "edited": True}]}
    assert s2.can_undo() is True
    assert s2.speech_name == "bot.json"
    assert s2.wavs == {"a.wav": b"\x00\x01RIFF"}     # bytes survive base64 roundtrip
    assert s2.transcript[0].tool_calls[0].name == "validate"
    assert s2.pending["proposed_data"] == {"k": 1}


def test_missing_file_returns_false(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    s = Session()
    assert persistence.load_session(s, "nope") is False


def test_corrupt_file_returns_false(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    sessions_dir = tmp_path / ".sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    p = sessions_dir / "corrupt.json"
    p.write_text("{ not json")
    s = Session()
    assert persistence.load_session(s, "corrupt") is False
