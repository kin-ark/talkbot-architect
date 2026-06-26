import json
import persistence
from fastapi.testclient import TestClient
from session import Session
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")
    main.STORE._active = Session()
    main.SESSION = main.STORE.active()


def _doc(name="Empty Dialogue"):
    return {"BizSpeechComponent": [], "BizSpeechScene": json.dumps({"speechName": name, "speechId": 1})}


def test_put_speech_name_sets_doc_payload_label_and_filename(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.post("/sessions")                 # create + activate a slot
        main.SESSION = main.STORE.active()
        main.STORE.active().load(_doc())

        r = client.put("/speech-name", json={"name": "Debt Collector"})
        assert r.status_code == 200 and r.json()["bot_name"] == "Debt Collector"

        # doc now carries the name + bot_name surfaces in GET /session
        payload = client.get("/session").json()
        assert payload["bot_name"] == "Debt Collector"

        # session label mirrored
        listed = client.get("/sessions").json()["sessions"]
        assert any(e["name"] == "Debt Collector" for e in listed)

        # export filename slugified
        exp = client.get("/export")
        assert "Debt_Collector.json" in exp.headers["content-disposition"]


def test_put_empty_name_400(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.post("/sessions")
        main.SESSION = main.STORE.active()
        main.STORE.active().load(_doc())
        assert client.put("/speech-name", json={"name": "   "}).status_code == 400


def test_apply_syncs_session_label_from_doc(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.post("/sessions")
        s = main.STORE.active()
        main.SESSION = s
        s.load(_doc("Empty Dialogue"))
        # stage a pending proposal whose proposed_data carries a real name
        s.pending = {"proposed_data": _doc("Survey Bot")}
        client.post("/apply")
        assert any(e["name"] == "Survey Bot" for e in client.get("/sessions").json()["sessions"])
