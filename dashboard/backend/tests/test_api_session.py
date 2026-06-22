import io, json
from pathlib import Path
from fastapi.testclient import TestClient
from main import app

_REAL = Path(__file__).resolve().parents[3] / "speech2572824560161596380.unpacked.json"
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
