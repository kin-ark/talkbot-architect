"""save_session is suppressed while a restore holds the guard."""
import persistence
from session import Session


def test_save_skipped_while_restore_guard_held(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path)
    s = Session()
    s.id = "x1"
    s.load({"BizSpeechComponent": "[]"})   # gives it a stack; also autosaves (guard not held yet)
    (tmp_path / "x1.json").unlink(missing_ok=True)

    with persistence.restore_guard():
        persistence.save_session(s)                 # must be dropped
        assert not (tmp_path / "x1.json").exists()

    persistence.save_session(s)                      # gate released -> writes
    assert (tmp_path / "x1.json").exists()
