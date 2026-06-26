import persistence
from fastapi.testclient import TestClient
from session import Session
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")
    main.STORE._active = Session()
    main.SESSION = main.STORE.active()


def test_sessions_list_carries_active_id(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        a = client.post("/sessions").json()
        body = client.get("/sessions").json()
        assert "active_id" in body
        assert body["active_id"] == a["id"]


def test_session_payload_carries_id_when_active(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        a = client.post("/sessions").json()
        payload = client.get("/session").json()
        assert payload["id"] == a["id"]
