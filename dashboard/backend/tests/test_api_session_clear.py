from fastapi.testclient import TestClient
import main


def test_clear_session_returns_to_empty():
    with TestClient(main.app) as client:
        client.get("/health")  # mint tbid
        tbid = client.cookies["tbid"]
        s = main.REGISTRY.store(tbid).active()
        s.load({"BizSpeechComponent": []})
        assert client.get("/session").json()["summary"] is not None
        r = client.post("/session/clear")
        assert r.status_code == 200
        assert r.json() == {"cleared": True}
        # after clearing, GET /session reports no session (landing screen)
        assert client.get("/session").json()["summary"] is None
    assert s._stack == []
    assert s.transcript == []
    assert s.pending is None
