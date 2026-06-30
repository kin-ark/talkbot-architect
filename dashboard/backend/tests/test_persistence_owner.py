import persistence
from session import Session


def _mk(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")


def test_owner_roundtrip_and_filter(tmp_path, monkeypatch):
    _mk(tmp_path, monkeypatch)
    a = Session()
    a.id = "s-a"
    a.owner = "alice"
    a._stack = [{"x": 1}]
    a._idx = 0
    b = Session()
    b.id = "s-b"
    b.owner = "bob"
    b._stack = [{"y": 2}]
    b._idx = 0
    persistence.save_session(a)
    persistence.save_session(b)
    alice_ids = {e["id"] for e in persistence.list_sessions("alice")}
    assert alice_ids == {"s-a"}
    assert {e["id"] for e in persistence.list_sessions("bob")} == {"s-b"}


def test_load_refuses_other_owner(tmp_path, monkeypatch):
    _mk(tmp_path, monkeypatch)
    a = Session()
    a.id = "s-a"
    a.owner = "alice"
    a._stack = [{"x": 1}]
    a._idx = 0
    persistence.save_session(a)
    dest = Session()
    assert persistence.load_session(dest, "s-a", owner="bob") is False
    assert persistence.load_session(dest, "s-a", owner="alice") is True
    assert dest.owner == "alice"


def test_per_owner_active_pointer(tmp_path, monkeypatch):
    _mk(tmp_path, monkeypatch)
    persistence.write_active("alice", "s-a")
    persistence.write_active("bob", "s-b")
    assert persistence.read_active("alice") == "s-a"
    assert persistence.read_active("bob") == "s-b"


def test_delete_owner_checked(tmp_path, monkeypatch):
    _mk(tmp_path, monkeypatch)
    a = Session()
    a.id = "s-a"
    a.owner = "alice"
    a._stack = [{"x": 1}]
    a._idx = 0
    persistence.save_session(a)
    persistence.delete_session("s-a", owner="bob")          # wrong owner → no-op
    assert persistence.list_sessions("alice")
    persistence.delete_session("s-a", owner="alice")
    assert not persistence.list_sessions("alice")
