import json
import persistence
from fastapi.testclient import TestClient
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")


def _doc(name="Empty Dialogue"):
    return {"BizSpeechComponent": [], "BizSpeechScene": json.dumps({"speechName": name, "speechId": 1})}


def test_put_speech_name_sets_doc_payload_label_and_filename(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.post("/sessions")                 # create + activate a slot
        # Load data into active session via registry
        tbid = client.cookies["tbid"]
        main.REGISTRY.store(tbid).active().load(_doc())

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
        tbid = client.cookies["tbid"]
        main.REGISTRY.store(tbid).active().load(_doc())
        assert client.put("/speech-name", json={"name": "   "}).status_code == 400


def test_apply_syncs_session_label_from_doc(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.post("/sessions")
        tbid = client.cookies["tbid"]
        s = main.REGISTRY.store(tbid).active()
        s.load(_doc("Empty Dialogue"))
        # stage a pending proposal whose proposed_data carries a real name
        s.pending = {"proposed_data": _doc("Survey Bot")}
        client.post("/apply")
        assert any(e["name"] == "Survey Bot" for e in client.get("/sessions").json()["sessions"])


def test_apply_returns_bot_name_in_response(tmp_path, monkeypatch):
    """POST /apply must return bot_name from the applied doc's speechName."""
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.post("/sessions")
        tbid = client.cookies["tbid"]
        s = main.REGISTRY.store(tbid).active()
        s.load(_doc("Empty Dialogue"))
        s.pending = {"proposed_data": _doc("Built Bot")}
        r = client.post("/apply")
        assert r.status_code == 200
        assert r.json()["bot_name"] == "Built Bot"


def test_undo_returns_reverted_bot_name_and_re_mirrors_label(tmp_path, monkeypatch):
    """After PUT /speech-name then POST /undo, the undo response carries the prior name
    and GET /sessions shows the session label reverted (re-mirrored)."""
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.post("/sessions")
        tbid = client.cookies["tbid"]
        s = main.REGISTRY.store(tbid).active()
        s.load(_doc("Empty Dialogue"))

        # rename to "New Name" — this pushes an undoable state
        r = client.put("/speech-name", json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["bot_name"] == "New Name"

        # undo the rename — doc reverts to "Empty Dialogue"
        r_undo = client.post("/undo")
        assert r_undo.status_code == 200
        data = r_undo.json()
        assert "bot_name" in data
        assert data["bot_name"] == "Empty Dialogue"

        # rail label should be re-mirrored to the reverted name
        listed = client.get("/sessions").json()["sessions"]
        assert any(e["name"] == "Empty Dialogue" for e in listed)
