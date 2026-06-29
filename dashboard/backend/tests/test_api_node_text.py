import copy
import json
from pathlib import Path

import agents
import persistence
from fastapi.testclient import TestClient
from session import Session
import main

_FIX = Path(__file__).resolve().parents[3] / "speech2572824560161596380.unpacked.json"
_DATA = json.loads(_FIX.read_text("utf-8"))


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")
    main.STORE._active = Session()
    main.SESSION = main.STORE.active()


def _load_fixture():
    main.STORE.new()
    main.SESSION = main.STORE.active()
    main.STORE.active().load(copy.deepcopy(_DATA))


def _first_talk_uuid(data):
    for comp in agents.unwrap(data.get("BizSpeechComponent")) or []:
        details = agents.unwrap(comp.get("details"))
        if isinstance(details, dict):
            for u, env in details.items():
                if isinstance(env, dict) and env.get("type") == 1:
                    return u
    return None


def _any_uuid(data):
    for comp in agents.unwrap(data.get("BizSpeechComponent")) or []:
        details = agents.unwrap(comp.get("details"))
        if isinstance(details, dict) and details:
            return next(iter(details))
    return None


def _summary_node(summary, uuid):
    for c in summary.get("components", []):
        if uuid in (c.get("nodes") or {}):
            return c["nodes"][uuid]
    return None


def test_component_index_of_resolves(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _load_fixture()
    u = _any_uuid(main.STORE.active().current())
    assert main._component_index_of(main.STORE.active().current(), u) is not None
    assert main._component_index_of(main.STORE.active().current(), "no-such-uuid") is None


def test_edit_label_changes_node_and_enables_undo(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _load_fixture()
    u = _any_uuid(main.STORE.active().current())
    with TestClient(main.app) as client:
        r = client.put(f"/node/{u}/text", json={"label": "Renamed Node"})
        assert r.status_code == 200
        body = r.json()
        assert body["can_undo"] is True
        assert _summary_node(body["summary"], u)["label"] == "Renamed Node"


def test_edit_prompt_changes_dialogue(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _load_fixture()
    u = _first_talk_uuid(main.STORE.active().current())
    assert u, "fixture must contain a talk node"
    with TestClient(main.app) as client:
        r = client.put(f"/node/{u}/text", json={"prompt": "Brand new line."})
        assert r.status_code == 200
        assert _summary_node(r.json()["summary"], u)["text"] == "Brand new line."


def test_unknown_uuid_404(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _load_fixture()
    with TestClient(main.app) as client:
        assert client.put("/node/no-such-uuid/text", json={"label": "X"}).status_code == 404


def test_empty_body_400(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _load_fixture()
    u = _any_uuid(main.STORE.active().current())
    with TestClient(main.app) as client:
        assert client.put(f"/node/{u}/text", json={"label": "   "}).status_code == 400
        assert client.put(f"/node/{u}/text", json={}).status_code == 400
