import persistence
from fastapi.testclient import TestClient
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")


def test_create_list_activate_rename_delete(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        a = client.post("/sessions").json()
        assert a["id"]
        b = client.post("/sessions").json()
        listed = client.get("/sessions").json()["sessions"]
        assert {e["id"] for e in listed} == {a["id"], b["id"]}

        r = client.post(f"/sessions/{a['id']}/activate")
        assert r.status_code == 200 and "summary" in r.json()

        assert client.patch(f"/sessions/{a['id']}", json={"name": "Renamed"}).json()["ok"]
        assert any(e["name"] == "Renamed" for e in client.get("/sessions").json()["sessions"])

        client.delete(f"/sessions/{b['id']}")
        assert {e["id"] for e in client.get("/sessions").json()["sessions"]} == {a["id"]}


def test_activate_missing_404(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        assert client.post("/sessions/missing/activate").status_code == 404


def test_activate_docless_session_returns_transcript():
    from llm.base import Message
    with TestClient(main.app) as client:
        client.get("/health")
        tbid = client.cookies["tbid"]
        store = main.REGISTRY.store(tbid)
        # New empty session (no doc stack), give it a chat transcript.
        sid = store.new().id
        sess = store.active()
        sess.transcript = [Message(role="user", content="hi"),
                           Message(role="assistant", content="hello")]
        persistence.save_session(sess)  # activate reloads from disk; persist the mutation first
        r = client.post(f"/sessions/{sid}/activate")
        assert r.status_code == 200
        body = r.json()
        assert body["summary"] is None
        assert len(body["transcript"]) == 2
        for k in ("proposal", "can_undo", "can_redo", "usage"):
            assert k in body
