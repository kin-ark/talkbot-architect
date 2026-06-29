import persistence
from fastapi.testclient import TestClient
from session import Session
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")
    main.STORE._active = Session()
    main.SESSION = main.STORE.active()


def test_list_samples(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        body = client.get("/samples").json()
        ids = {e["id"] for e in body}
        assert {"greeting_faq", "debt_collector", "appointment_booking"} <= ids
        assert all({"id", "title", "description"} == set(e) for e in body)


def test_load_sample_creates_clean_session(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        r = client.post("/samples/greeting_faq")
        assert r.status_code == 200
        body = r.json()
        assert "summary" in body
        assert [f for f in body["findings"] if f["severity"] == "error"] == []
        # session created + active
        assert any(e["name"] == "Greeting & FAQ" for e in client.get("/sessions").json()["sessions"])


def test_unknown_sample_404(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        assert client.post("/samples/nope").status_code == 404
