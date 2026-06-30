import persistence
from session_store import SessionStore


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")


def test_new_creates_identified_active(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    store = SessionStore()
    a = store.new(name="Bot A")
    assert a is store.active() and a.id and a.name == "Bot A"
    assert persistence.read_active("_legacy") == a.id


def test_activate_swaps_contents_same_object(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    store = SessionStore()
    a = store.new(name="A")
    a.load({"BizSpeechComponent": []})
    a.name = "A"
    persistence.save_session(a)
    a_id = a.id
    b = store.new(name="B")
    b.load({"BizSpeechComponent": []})
    b.name = "B"
    persistence.save_session(b)
    obj = store.active()                       # stable object identity
    assert store.activate(a_id) is True
    assert store.active() is obj               # same object, swapped contents
    assert store.active().name == "A"


def test_list_and_delete_active_falls_back(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    store = SessionStore()
    a = store.new(name="A")
    a.load({"BizSpeechComponent": []})
    persistence.save_session(a)
    b = store.new(name="B")
    b.load({"BizSpeechComponent": []})
    persistence.save_session(b)  # b active
    assert len(store.list()) == 2
    store.delete(b.id)
    assert {e["id"] for e in store.list()} == {a.id}
    assert store.active().id == a.id           # fell back to remaining
