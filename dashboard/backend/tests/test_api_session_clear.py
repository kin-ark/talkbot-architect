from fastapi.testclient import TestClient
import main


def test_clear_session_returns_to_empty():
    main.SESSION.load({"BizSpeechComponent": []})
    with TestClient(main.app) as client:
        assert client.get("/session").json()["summary"] is not None
        r = client.post("/session/clear")
        assert r.status_code == 200
        assert r.json() == {"cleared": True}
        # after clearing, GET /session reports no session (landing screen)
        assert client.get("/session").json()["summary"] is None
    assert main.SESSION._stack == []
    assert main.SESSION.transcript == []
    assert main.SESSION.pending is None
