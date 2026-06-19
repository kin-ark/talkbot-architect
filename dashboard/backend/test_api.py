from fastapi.testclient import TestClient
from dashboard.backend.main import app

client = TestClient(app)

def test_analyze_upload():
    content = b'{"BizSpeechComponent": "[]"}'
    response = client.post("/analyze", files={"file": ("speech.json", content)})
    assert response.status_code == 200
    assert "summary" in response.json()

def test_chat_endpoint():
    payload = {
        "message": "Tell me about my errors",
        "context": {"errors": 5}
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    assert response.json()["response"] == "I see you have 5 errors. How can I help?"

def test_summarize_endpoint():
    content = b'{"BizSpeechComponent": "[]"}'
    response = client.post("/summarize", files={"file": ("test.json", content)})
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    # Empty component means empty summary tree
    assert data["summary"] == {}

def test_analyze_invalid_json():
    content = b'this is not json'
    response = client.post("/analyze", files={"file": ("speech.json", content)})
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]

def test_analyze_invalid_export():
    # Valid JSON but not a valid talkbot export (wrong type for component)
    content = b'{"BizSpeechComponent": 123}'
    response = client.post("/analyze", files={"file": ("speech.json", content)})
    assert response.status_code == 400
    assert "Invalid Talkbot Export" in response.json()["detail"]
