import agents
from fastapi.testclient import TestClient
import main


def test_list_intents_user_system_and_counts():
    data = {"SpeechIntent": [
        {"intentId": "1", "intentName": "Charge Confirmation", "isInit": 1,
         "keyWordInIntent": "yes,confirm,ok", "userResponseInIntent": "yes please;confirmed"},
        {"intentId": "2", "intentName": "IOS Enter", "isInit": 0,
         "keyWordInIntent": "", "userResponseInIntent": ""},
        {"intentId": "3", "intentName": "Empty User", "isInit": 1,
         "keyWordInIntent": "", "userResponseInIntent": ""},
        "not-a-dict",
        {"intentId": "4", "isInit": 1},                       # missing name -> skipped
    ]}
    out = agents.list_intents(data)
    assert [i["name"] for i in out] == ["Charge Confirmation", "IOS Enter", "Empty User"]
    charge, ios, empty = out
    assert charge["type"] == "user" and charge["keyword_count"] == 3 and charge["response_count"] == 2
    assert charge["needs_nlu"] is False
    assert ios["type"] == "system" and ios["needs_nlu"] is False   # system never needs_nlu
    assert empty["type"] == "user" and empty["needs_nlu"] is True   # WIZ305


def test_list_intents_empty():
    assert agents.list_intents({}) == []
    assert agents.list_intents({"SpeechIntent": []}) == []


def test_get_intents_blank_session_returns_empty(tmp_path, monkeypatch):
    import persistence
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    main.REGISTRY.reset()
    with TestClient(main.app) as client:
        client.post("/session/blank")                 # loads {"BizSpeechComponent": []}
        r = client.get("/intents")
        assert r.status_code == 200
        assert r.json() == []
