import json
import persistence
from fastapi.testclient import TestClient
from llm.base import FakeLLMClient, LLMResponse
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")
    main.STORE._active = main.Session()
    main.SESSION = main.STORE.active()


def _events(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def test_chat_stream_emits_usage_and_session_payload_carries_it(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    fake = FakeLLMClient(script=[LLMResponse(text="ok", tool_calls=[])],
                         usage=[{"input_tokens": 12, "output_tokens": 5}])
    fake.model = "m-test"
    main.app.dependency_overrides[main.get_client] = lambda: fake
    try:
        main.STORE.new()
        main.SESSION.load({"BizSpeechComponent": []})
        with TestClient(main.app) as client:
            evs = _events(client.post("/chat/stream", json={"message": "hi"}).text)
            assert any(e["type"] == "usage" and e["input_tokens"] == 12 for e in evs)
            payload = client.get("/session").json()
            assert payload["usage"]["input_tokens"] == 12 and payload["usage"]["turns"] == 1
    finally:
        main.app.dependency_overrides.clear()
