import json
from fastapi.testclient import TestClient
from llm.base import LLMClient, LLMResponse, ToolCall
import main


SCAFFOLD_ARGS = {
    "name": "Debt Collector", "language": "ENG", "branch": "dev",
    "canvases": [{"name": "1. Greeting",
                  "nodes": [{"id": "g-root", "prompt": "Greeting"},
                            {"id": "g-close", "prompt": "Closing"}],
                  "edges": [{"from": "g-root", "branch": "Unclassified", "to": "g-close"}]}],
}


def test_scaffold_chat_to_export_is_checker_clean():
    # No session loaded yet — scaffold_bot creates the first doc, so the chat
    # must run without a prior /session. Seed an empty doc so _require_session
    # passes, then scaffold replaces it on apply.
    main.SESSION.load({"BizSpeechComponent": []})

    script = [
        LLMResponse(text=None, tool_calls=[ToolCall("c1", "scaffold_bot", SCAFFOLD_ARGS)]),
        LLMResponse(text="Scaffolded your Debt Collector bot. Review the diff.", tool_calls=[]),
    ]

    class _Fake(LLMClient):
        def __init__(self): self.i = 0
        def chat(self, messages, tools):
            r = script[self.i]; self.i += 1; return r

    main.app.dependency_overrides[main.get_client] = lambda: _Fake()
    client = TestClient(main.app)
    try:
        r = client.post("/chat", json={"message": "make me a Debt Collector talkbot"})
        assert r.status_code == 200, r.text
        assert r.json()["proposal"] is not None
        ap = client.post("/apply")
        assert ap.status_code == 200, ap.text
        assert ap.json()["applied"] is True
        # exported doc parses and is checker-clean (no error findings)
        ex = client.get("/export")
        assert ex.status_code == 200
        doc = json.loads(ex.content)
        errors = [f for f in ap.json()["findings"] if f["severity"] == "error"]
        assert errors == [], errors
        assert "BizSpeechComponent" in doc
    finally:
        main.app.dependency_overrides.clear()
