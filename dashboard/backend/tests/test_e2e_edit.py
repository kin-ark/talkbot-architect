from fastapi.testclient import TestClient
from llm.base import LLMClient, LLMResponse, ToolCall
import main

# Real-ish session: one empty component to add a node to.
# componentUuid must be a valid UUID — the checker's parser enforces this.
# createTime/updateTime must be non-zero (WIZ005); SpeechVariable + SpeechAudio
# must be present (WIZ001 required-key check).
DATA = {
    "BizSpeechComponent": [{"componentUuid": "00000000-0000-0000-0000-000000000001",
                            "name": "Main", "speechId": 1,
                            "details": "null", "routes": "{}", "inboundPorts": "[]",
                            "createTime": 1700000000000, "updateTime": 1700000000000}],
    "SpeechIntent": [{"intentName": n, "intentId": i} for i, n in
                     enumerate(["Positive", "Negative", "Reject", "Unclassified", "No answer"], 1)],
    "SpeechVariable": [],
    "SpeechAudio": [],
    "BizKnowledgeInfo": [],
}


def test_chat_add_node_apply():
    script = [
        LLMResponse(text=None, tool_calls=[ToolCall("c1", "add_node",
                    {"component": 0, "id": "greet", "prompt": "Greeting"})]),
        LLMResponse(text="Added a greeting node — review the diff.", tool_calls=[]),
    ]

    class _Fake(LLMClient):
        def __init__(self):
            self.i = 0

        def chat(self, messages, tools):
            r = script[self.i]
            self.i += 1
            return r

    main.app.dependency_overrides[main.get_client] = lambda: _Fake()
    with TestClient(main.app) as client:
        client.get("/health")  # mint tbid
        tbid = client.cookies["tbid"]
        main.REGISTRY.store(tbid).active().load(DATA)
        try:
            r = client.post("/chat", json={"message": "add a greeting node to Main"})
            assert r.status_code == 200, r.text
            assert r.json()["proposal"] is not None
            ap = client.post("/apply")
            assert ap.status_code == 200, ap.text
            errors = [f for f in ap.json()["findings"] if f["severity"] == "error"]
            assert errors == [], errors
        finally:
            main.app.dependency_overrides.clear()
