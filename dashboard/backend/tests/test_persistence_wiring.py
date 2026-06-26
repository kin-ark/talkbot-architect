import persistence
from session import Session


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")


def test_apply_autosaves(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    sessions_dir = tmp_path / ".sessions"
    s = Session()
    s.id = "wiring1"
    s.load({"BizSpeechComponent": []})
    assert (sessions_dir / "wiring1.json").exists()   # load() autosaved via _autosave
    s.apply({"BizSpeechComponent": [{"x": 1}]})
    reloaded = Session()
    assert persistence.load_session(reloaded, "wiring1") is True
    assert reloaded.current() == {"BizSpeechComponent": [{"x": 1}]}


def test_save_failure_does_not_raise(tmp_path, monkeypatch):
    # Override save_session to raise; mutation must still succeed.
    monkeypatch.setattr(persistence, "save_session",
                        lambda s: (_ for _ in ()).throw(OSError("boom")))
    s = Session()
    s.id = "wiring2"
    s.load({"BizSpeechComponent": []})              # must not raise
