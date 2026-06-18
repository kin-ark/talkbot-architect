from fastapi.testclient import TestClient
from dashboard.backend.main import app

client = TestClient(app)

def test_analyze_upload():
    content = b'{"BizSpeechComponent": "[]"}'
    response = client.post("/analyze", files={"file": ("speech.json", content)})
    assert response.status_code == 200
    assert "summary" in response.json()
