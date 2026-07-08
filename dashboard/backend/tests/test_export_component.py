import json
import pytest
import agents
import samples
import persistence
from wizcheck.component_adapter import is_component_export
from fastapi.testclient import TestClient
import main


def _full():
    # a multi-component full bot
    b = agents.propose_build(samples.load_manifest("debt_dpd1_5"))
    assert b["ok"], b.get("error")
    return b["proposed_data"]


def _comps(data):
    v = data.get("BizSpeechComponent")
    return json.loads(v) if isinstance(v, str) else (v or [])


def test_whole_dialog_exports_all_components():
    data = agents.propose_build(samples.load_manifest("greeting_faq"))["proposed_data"]
    dto = agents.export_component_dto(data, None)
    assert is_component_export(dto)
    assert len(dto["componentImportAndExportDTOS"]) == len(_comps(data))


def test_picker_exports_single_component():
    data = _full()
    comps = _comps(data)
    uuid = comps[0]["componentUuid"]
    dto = agents.export_component_dto(data, uuid)
    assert is_component_export(dto)
    got = {e["componentUuid"] for e in dto["componentImportAndExportDTOS"]}
    # the picked component is present; total < all (true subset)
    assert uuid in got
    assert len(got) < len(comps)


def test_unknown_uuid_raises():
    data = _full()
    with pytest.raises(KeyError):
        agents.export_component_dto(data, "no-such-uuid")


def test_export_component_does_not_mutate_input():
    data = _full()
    before = json.dumps(data, sort_keys=True, default=str)
    agents.export_component_dto(data, _comps(data)[0]["componentUuid"])
    assert json.dumps(data, sort_keys=True, default=str) == before


def _cd_filename(resp):
    return resp.headers["content-disposition"].split("filename=", 1)[1].strip().strip('"')


def test_api_export_component_whole_dialog(tmp_path, monkeypatch):
    """GET /export/component (no uuid) → 200 with ZIP bundle (components + intent/KB Excel)"""
    import zipfile
    import io
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    with TestClient(main.app) as client:
        # Load a full bot
        client.post("/samples/greeting_faq")
        r = client.get("/export/component")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        filename = _cd_filename(r)
        assert filename.endswith(".components.zip")
        # Verify ZIP contents
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        # Should have component JSON(s) and Excel files
        assert any(".component.json" in name for name in names), f"No .component.json in {names}"
        assert any("intents.xls" in name for name in names), f"No intents.xls in {names}"
        assert any("KB.xls" in name for name in names), f"No KB.xls in {names}"


def test_api_export_component_single_uuid(tmp_path, monkeypatch):
    """GET /export/component?uuid=<known> → 200 with single-component envelope"""
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    with TestClient(main.app) as client:
        # Load a multi-component bot and extract a component uuid
        manifest = samples.load_manifest("debt_dpd1_5")
        build_resp = agents.propose_build(manifest)
        assert build_resp["ok"], build_resp.get("error")
        built_data = build_resp["proposed_data"]
        comps = _comps(built_data)
        assert len(comps) > 0, "Expected at least one component"
        uuid = comps[0]["componentUuid"]

        # Load the same bot into the session
        client.post("/samples/debt_dpd1_5")

        # Export with the uuid
        r = client.get(f"/export/component?uuid={uuid}")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/json"
        dto = json.loads(r.content)
        assert is_component_export(dto)
        # The picked component must be in the result
        got_uuids = {e["componentUuid"] for e in dto["componentImportAndExportDTOS"]}
        assert uuid in got_uuids


def test_api_export_component_unknown_uuid(tmp_path, monkeypatch):
    """GET /export/component?uuid=bad → 404"""
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    with TestClient(main.app) as client:
        client.post("/samples/greeting_faq")
        r = client.get("/export/component?uuid=no-such-uuid")
        assert r.status_code == 404


def test_api_export_component_from_component_session(tmp_path, monkeypatch):
    """GET /export/component from a component session → 400"""
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    with TestClient(main.app) as client:
        # Build a full bot and export it as a component envelope
        data = agents.propose_build(samples.load_manifest("greeting_faq"))["proposed_data"]
        dto = agents.export_component_dto(data, None)
        # Upload the component envelope to make the session a component session
        files = {"file": ("comp.json", json.dumps(dto).encode("utf-8"), "application/json")}
        r = client.post("/session", files=files)
        assert r.status_code == 200
        # Now try to export as component from a component session → 400
        r = client.get("/export/component")
        assert r.status_code == 400
