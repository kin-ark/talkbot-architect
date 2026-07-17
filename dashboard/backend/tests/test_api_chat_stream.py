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
    pass


def teardown_function():
    main.app.dependency_overrides.clear()


def test_chat_stream_emits_token_and_done():
    _use_fake([LLMResponse(text="all good", tool_calls=[])])
    with TestClient(main.app) as client:
        client.get("/health")  # mint tbid
        tbid = client.cookies["tbid"]
        main.REGISTRY.store(tbid).active().load({"BizSpeechComponent": "[]"})
        r = client.post("/chat/stream", json={"message": "hi"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        events = _events_from_sse(r.text)
    types = [e["type"] for e in events]
    assert "token" in types
    assert events[-1]["type"] == "done"
    assert events[-1]["text"] == "all good"


def test_chat_stream_heartbeats_during_silence(monkeypatch):
    """A turn that stays silent past the heartbeat interval must still emit an
    immediate first byte + keepalive comments, so a proxy never 524s it."""
    import time as _t
    monkeypatch.setattr(main, "_HEARTBEAT_S", 0.05)

    def _slow_turn(_client, _s, _message):
        _t.sleep(0.15)  # silent stretch longer than the heartbeat interval
        yield {"type": "token", "delta": "hi"}
        yield {"type": "done", "canceled": False, "text": "hi"}

    monkeypatch.setattr(main, "run_turn_stream", _slow_turn)
    _use_fake([LLMResponse(text="x", tool_calls=[])])
    with TestClient(main.app) as client:
        client.get("/health")  # mint tbid
        tbid = client.cookies["tbid"]
        main.REGISTRY.store(tbid).active().load({"BizSpeechComponent": "[]"})
        raw = client.post("/chat/stream", json={"message": "hi"}).text
    assert ": open" in raw   # immediate byte -> proxy commits headers now
    assert ": ping" in raw   # keepalive fired during the silent stretch
    events = _events_from_sse(raw)
    assert events[-1]["type"] == "done" and events[-1]["text"] == "hi"


def test_chat_stream_emits_tool_and_proposal():
    _use_fake([
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="validate", arguments={})]),
        LLMResponse(text="done", tool_calls=[]),
    ])
    with TestClient(main.app) as client:
        client.get("/health")  # mint tbid
        tbid = client.cookies["tbid"]
        main.REGISTRY.store(tbid).active().load({"BizSpeechComponent": "[]"})
        events = _events_from_sse(client.post("/chat/stream", json={"message": "check"}).text)
    types = [e["type"] for e in events]
    assert "tool_start" in types and "tool_result" in types
