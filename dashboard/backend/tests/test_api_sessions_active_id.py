import persistence
from fastapi.testclient import TestClient
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")


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


def test_delete_last_session_clears_active_id(tmp_path, monkeypatch):
    """Deleting the only session must clear the on-disk active pointer.

    After deletion, GET /sessions must report active_id as None and the
    DELETE response must have active == null.
    """
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        a = client.post("/sessions").json()
        assert a["id"]

        # Confirm active_id is set before deletion.
        before = client.get("/sessions").json()
        assert before["active_id"] == a["id"]

        # Delete the only session.
        del_resp = client.delete(f"/sessions/{a['id']}").json()
        assert del_resp["active"] is None

        # GET /sessions must now report active_id as None and empty list.
        after = client.get("/sessions").json()
        assert after["sessions"] == []
        assert after["active_id"] is None
