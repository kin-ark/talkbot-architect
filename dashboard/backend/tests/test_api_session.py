from pathlib import Path
from fastapi.testclient import TestClient
from main import app

_REAL = Path(__file__).resolve().parent / "fixtures" / "sample_export.json"
_COMPONENT_EXPORT = Path(__file__).resolve().parents[3] / ".claude" / "skills" / "wiz-checker" / "tests" / "fixtures" / "component_export_min.json"
client = TestClient(app)


def test_upload_then_summary_and_findings():
    files = {"file": ("speech.json", _REAL.read_bytes(), "application/json")}
    r = client.post("/session", files=files)
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body and "findings" in body
    s = client.get("/summary").json()
    assert "components" in s
    f = client.get("/findings").json()
    assert isinstance(f, list)


def test_bad_upload_returns_400():
    files = {"file": ("x.json", b"not json", "application/json")}
    r = client.post("/session", files=files)
    assert r.status_code == 400


def test_component_export_upload():
    """Test that a component-export (componentImportAndExportDTOS envelope) parses
    + validates without error through the dashboard backend.
    The parse_dict hook auto-detects and adapts it to full-export shape.
    """
    files = {"file": ("component.json", _COMPONENT_EXPORT.read_bytes(), "application/json")}
    r = client.post("/session", files=files)
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body and "findings" in body
    # Findings should be a list (even if empty or with warnings)
    assert isinstance(body["findings"], list)
    # Bot-scope codes should not appear (they are suppressed in component mode)
    findings_codes = {f["code"] for f in body["findings"]}
    bot_scope_codes = {"WIZ104", "WIZ110", "WIZ202", "WIZ303"}
    assert not (findings_codes & bot_scope_codes), \
        f"bot-scope codes should be suppressed in component mode, but found: {findings_codes & bot_scope_codes}"
