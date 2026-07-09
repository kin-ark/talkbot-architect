import copy
import json
from pathlib import Path

import agents
import persistence
from fastapi.testclient import TestClient
import main

_FIX = Path(__file__).resolve().parent / "fixtures" / "sample_export.json"
_DATA = json.loads(_FIX.read_text("utf-8"))


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")


def _load_fixture(client):
    tbid = client.cookies["tbid"]
    store = main.REGISTRY.store(tbid)
    store.new()
    store.active().load(copy.deepcopy(_DATA))
    return store


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
    with TestClient(main.app) as client:
        client.get("/health")   # mint tbid
        store = _load_fixture(client)
        u = _any_uuid(store.active().current())
        assert main._component_index_of(store.active().current(), u) is not None
        assert main._component_index_of(store.active().current(), "no-such-uuid") is None


def test_edit_label_changes_node_and_enables_undo(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.get("/health")   # mint tbid
        store = _load_fixture(client)
        u = _any_uuid(store.active().current())
        r = client.put(f"/node/{u}/text", json={"label": "Renamed Node"})
        assert r.status_code == 200
        body = r.json()
        assert body["can_undo"] is True
        assert _summary_node(body["summary"], u)["label"] == "Renamed Node"


def test_edit_prompt_changes_dialogue(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.get("/health")   # mint tbid
        store = _load_fixture(client)
        u = _first_talk_uuid(store.active().current())
        assert u, "fixture must contain a talk node"
        r = client.put(f"/node/{u}/text", json={"prompt": "Brand new line."})
        assert r.status_code == 200
        assert _summary_node(r.json()["summary"], u)["text"] == "Brand new line."


def test_unknown_uuid_404(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.get("/health")   # mint tbid
        _load_fixture(client)
        assert client.put("/node/no-such-uuid/text", json={"label": "X"}).status_code == 404


def test_empty_body_400(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        client.get("/health")   # mint tbid
        store = _load_fixture(client)
        u = _any_uuid(store.active().current())
        assert client.put(f"/node/{u}/text", json={"label": "   "}).status_code == 400
        assert client.put(f"/node/{u}/text", json={}).status_code == 400
