import threading
import time
from fastapi.testclient import TestClient
from llm.base import LLMClient, LLMResponse
import main


class _SlowClient(LLMClient):
    """Records concurrent entry; sleeps so overlap is observable.

    Subclasses LLMClient so it inherits the default stream_chat (which wraps
    chat) — run_turn now drives the client through stream_chat."""
    active = 0
    max_active = 0
    lock = threading.Lock()

    def chat(self, messages, tools):
        with _SlowClient.lock:
            _SlowClient.active += 1
            _SlowClient.max_active = max(_SlowClient.max_active, _SlowClient.active)
        time.sleep(0.2)
        with _SlowClient.lock:
            _SlowClient.active -= 1
        return LLMResponse(text="ok", tool_calls=[])


def test_chat_is_serialized_per_session():
    main.SESSION.load({"BizSpeechComponent": []})
    main.app.dependency_overrides[main.get_client] = lambda: _SlowClient()
    client = TestClient(main.app)
    try:
        results = []
        threads = [threading.Thread(target=lambda: results.append(client.post("/chat", json={"message": "hi"})))
                   for _ in range(2)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert all(r.status_code == 200 for r in results)
        assert _SlowClient.max_active == 1     # never two turns at once
    finally:
        main.app.dependency_overrides.clear()


def test_cancel_endpoint_sets_flag():
    main.SESSION.load({"BizSpeechComponent": []})
    client = TestClient(main.app)
    r = client.post("/chat/cancel")
    assert r.status_code == 200
    assert r.json()["canceling"] is True
    assert main.SESSION.cancel_requested is True
