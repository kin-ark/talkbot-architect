import persistence
from session import Session
from llm.base import Message, ToolCall


def test_roundtrip_full_state(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "STATE_PATH", tmp_path / "state.json")
    s = Session()
    s.load({"BizSpeechComponent": [{"componentUuid": "c1"}]},
           speech_name="bot.json", wavs={"a.wav": b"\x00\x01RIFF"})
    s.apply({"BizSpeechComponent": [{"componentUuid": "c1", "edited": True}]})
    s.transcript.append(Message(role="assistant", content="hi",
                                tool_calls=[ToolCall("t1", "validate", {})]))
    s.pending = {"diff": "x", "proposed_data": {"k": 1}}
    persistence.save_session(s)

    s2 = Session()
    assert persistence.load_session(s2) is True
    assert s2.current() == {"BizSpeechComponent": [{"componentUuid": "c1", "edited": True}]}
    assert s2.can_undo() is True
    assert s2.speech_name == "bot.json"
    assert s2.wavs == {"a.wav": b"\x00\x01RIFF"}     # bytes survive base64 roundtrip
    assert s2.transcript[0].tool_calls[0].name == "validate"
    assert s2.pending["proposed_data"] == {"k": 1}


def test_missing_file_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "STATE_PATH", tmp_path / "nope.json")
    s = Session()
    assert persistence.load_session(s) is False


def test_corrupt_file_returns_false(tmp_path, monkeypatch):
    p = tmp_path / "state.json"
    p.write_text("{ not json")
    monkeypatch.setattr(persistence, "STATE_PATH", p)
    s = Session()
    assert persistence.load_session(s) is False
