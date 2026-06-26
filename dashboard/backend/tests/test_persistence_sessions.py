import json
import persistence
from session import Session


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")


def test_save_load_roundtrip_with_metadata(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    s = Session()
    s.id = "abc123"; s.name = "Greeting bot"
    s.usage = {"input_tokens": 5, "output_tokens": 7, "turns": 1, "model": "claude-x"}
    s.load({"BizSpeechComponent": []})   # _autosave writes the snapshot
    s.id = "abc123"; s.name = "Greeting bot"   # load() may reset; re-set then save
    s.usage = {"input_tokens": 5, "output_tokens": 7, "turns": 1, "model": "claude-x"}
    persistence.save_session(s)

    s2 = Session()
    assert persistence.load_session(s2, "abc123") is True
    assert s2.name == "Greeting bot"
    assert s2.usage["input_tokens"] == 5 and s2.usage["model"] == "claude-x"
    assert s2.current() == {"BizSpeechComponent": []}


def test_list_and_delete(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    for sid, name in [("a", "A"), ("b", "B")]:
        s = Session(); s.id = sid; s.name = name; s.load({"BizSpeechComponent": []})
        s.id = sid; s.name = name; persistence.save_session(s)
    listed = persistence.list_sessions()
    assert {e["id"] for e in listed} == {"a", "b"}
    assert all("usage" in e and "name" in e for e in listed)
    persistence.delete_session("a")
    assert {e["id"] for e in persistence.list_sessions()} == {"b"}


def test_active_pointer(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert persistence.read_active() is None
    persistence.write_active("xyz")
    assert persistence.read_active() == "xyz"


def test_legacy_migration(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    legacy = tmp_path / ".session" / "state.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"stack": [{"BizSpeechComponent": []}], "idx": 0,
        "transcript": [], "pending": None, "speech_name": "old.json", "wavs": {}}), encoding="utf-8")
    monkeypatch.setattr(persistence, "LEGACY_PATH", legacy)
    s = Session()
    assert persistence.migrate_legacy(s) is True
    assert s.id and s.current() == {"BizSpeechComponent": []}
    assert persistence.read_active() == s.id     # migrated snapshot is active
