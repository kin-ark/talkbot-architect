import json
import pathlib

import agents
import persistence
from fastapi.testclient import TestClient
from wizcheck.component_adapter import component_export_to_full, is_component_export

import main

FIX = pathlib.Path(__file__).parent / "fixtures" / "component_export_min.json"


def test_component_export_warnings():
    # a full doc with a KB → warning; empty → none
    with_kb = {"BizKnowledgeInfo": [{"kdTitle": "K"}]}
    assert agents.component_export_warnings(with_kb)
    assert agents.component_export_warnings({"BizSpeechComponent": []}) == []


def test_export_roundtrip_yields_component_envelope():
    raw = json.loads(FIX.read_text(encoding="utf-8"))
    full = component_export_to_full(raw)
    from wizcheck.component_adapter import full_to_component_export
    dto = full_to_component_export(full, base=raw, name=None)
    assert is_component_export(dto)


def test_api_component_export(tmp_path, monkeypatch):
    """Test that uploading a component export and then exporting it back yields
    a component envelope with the right filename."""
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    with TestClient(main.app) as client:
        # Upload the component fixture
        raw_fixture = FIX.read_bytes()
        files = {"file": ("component.json", raw_fixture, "application/json")}
        r = client.post("/session", files=files)
        assert r.status_code == 200

        # Check session shows is_component
        session_resp = client.get("/session").json()
        assert session_resp.get("is_component") is True

        # Export should return component envelope
        export_resp = client.get("/export")
        assert export_resp.status_code == 200
        assert export_resp.headers["content-type"] == "application/json"

        # Check filename ends with .component.json
        content_disp = export_resp.headers.get("content-disposition", "")
        assert "filename=" in content_disp
        filename = content_disp.split("filename=", 1)[1].strip().strip('"')
        assert filename.endswith(".component.json")

        # Check body is a component envelope
        exported = json.loads(export_resp.content)
        assert is_component_export(exported)


def test_session_upload_response_includes_is_component(tmp_path, monkeypatch):
    """Test that POST /session response includes is_component and component_warnings fields."""
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    with TestClient(main.app) as client:
        # Upload the component fixture
        raw_fixture = FIX.read_bytes()
        files = {"file": ("component.json", raw_fixture, "application/json")}
        r = client.post("/session", files=files)
        assert r.status_code == 200

        # Check response includes is_component and component_warnings
        body = r.json()
        assert "is_component" in body
        assert body["is_component"] is True
        assert "component_warnings" in body
        assert isinstance(body["component_warnings"], list)
