from fastapi.testclient import TestClient
import main


def test_blank_session_creates_session():
    client = TestClient(main.app)
    r = client.post("/session/blank")
    assert r.status_code == 200, r.text
    assert "summary" in r.json()
    assert "findings" in r.json()


def test_chat_allowed_after_blank(monkeypatch):
    # After a blank session, /summary must not 503 (session exists).
    client = TestClient(main.app)
    client.post("/session/blank")
    r = client.get("/summary")
    assert r.status_code == 200, r.text
