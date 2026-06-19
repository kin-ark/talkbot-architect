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
    assert "mainFlow" in data
    # Empty component means empty summary tree
    assert data == {"mainFlow": [], "knowledgeBases": []}

def test_summarize_endpoint_with_data():
    import json
    payload = {
        "BizSpeechComponent": json.dumps([{
            "uuid": "c01f65d6-0c19-410a-8bf8-024ce1ecfb2a",
            "componentUuid": "c01f65d6-0c19-410a-8bf8-024ce1ecfb2a",
            "speechId": 1,
            "branch": "main",
            "componentName": "Test",
            "category": 2,
            "details": json.dumps({
                "list": [{
                    "uuid": "11111111-1111-1111-1111-111111111111",
                    "parentUuid": "",
                    "label": "Talk Node",
                    "sortIndex": 1,
                    "data": {"allow_jump_knowledges": [1]}
                }],
                "rootUuids": ["11111111-1111-1111-1111-111111111111"]
            })
        }]),
        "BizKnowledgeInfo": json.dumps([{
            "knowledgeId": 1,
            "title": "KB1",
            "kdType": 1,
            "intents": []
        }])
    }
    content = json.dumps(payload).encode()
    response = client.post("/summarize", files={"file": ("test.json", content)})
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert "mainFlow" in data
    assert "knowledgeBases" in data
    
    assert len(data["knowledgeBases"]) == 1
    assert data["knowledgeBases"][0]["title"] == "KB1"
    
    assert len(data["mainFlow"]) == 1
    assert len(data["mainFlow"][0]["children"]) == 1
    node = data["mainFlow"][0]["children"][0]
    assert node["name"] == "Talk Node"
    assert node["node_type"] == 2
    assert node["allowedKBs"] == [1]

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
