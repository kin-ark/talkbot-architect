import json
from pathlib import Path
from fastapi.testclient import TestClient
import main
from main import app

_REAL = Path(__file__).resolve().parents[3] / "speech2572824560161596380.unpacked.json"
client = TestClient(app)


def test_export_returns_valid_json():
    main.SESSION.load(json.loads(_REAL.read_text(encoding="utf-8")))
    r = client.get("/export")
    assert r.status_code == 200
    assert "application/json" in r.headers["content-type"]
    data = json.loads(r.content)
    assert "BizSpeechComponent" in data
