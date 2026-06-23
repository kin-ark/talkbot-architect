import persistence
from session import Session


def test_apply_autosaves(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "STATE_PATH", tmp_path / "state.json")
    s = Session()
    s.load({"BizSpeechComponent": []})
    assert persistence.STATE_PATH.exists()          # load() autosaved
    s.apply({"BizSpeechComponent": [{"x": 1}]})
    reloaded = Session()
    assert persistence.load_session(reloaded) is True
    assert reloaded.current() == {"BizSpeechComponent": [{"x": 1}]}


def test_save_failure_does_not_raise(tmp_path, monkeypatch):
    # Point at an unwritable path; mutation must still succeed.
    monkeypatch.setattr(persistence, "STATE_PATH", tmp_path / "nodir" / "x" / "state.json")
    monkeypatch.setattr(persistence, "save_session",
                        lambda s: (_ for _ in ()).throw(OSError("boom")))
    s = Session()
    s.load({"BizSpeechComponent": []})              # must not raise
