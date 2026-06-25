import json
from fastapi.testclient import TestClient
import main
from llm.base import FakeLLMClient, LLMResponse, ToolCall


def _events_from_sse(text):
    out = []
    for line in text.splitlines():
        if line.startswith("data: "):
            out.append(json.loads(line[len("data: "):]))
    return out


def _use_fake(script):
    main.app.dependency_overrides[main.get_client] = lambda: FakeLLMClient(script)


def setup_function():
    main.SESSION.load({"BizSpeechComponent": "[]"})


def teardown_function():
    main.app.dependency_overrides.clear()


def test_chat_stream_emits_token_and_done():
    _use_fake([LLMResponse(text="all good", tool_calls=[])])
    with TestClient(main.app) as client:
        r = client.post("/chat/stream", json={"message": "hi"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        events = _events_from_sse(r.text)
    types = [e["type"] for e in events]
    assert "token" in types
    assert events[-1]["type"] == "done"
    assert events[-1]["text"] == "all good"


def test_chat_stream_emits_tool_and_proposal():
    _use_fake([
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="validate", arguments={})]),
        LLMResponse(text="done", tool_calls=[]),
    ])
    with TestClient(main.app) as client:
        events = _events_from_sse(client.post("/chat/stream", json={"message": "check"}).text)
    types = [e["type"] for e in events]
    assert "tool_start" in types and "tool_result" in types
