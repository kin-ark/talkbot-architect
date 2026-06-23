from fastapi.testclient import TestClient
from llm.base import LLMResponse
import main


class _BoomClient:
    def chat(self, messages, tools):
        raise RuntimeError("provider exploded")


def test_unhandled_exception_returns_error_shape():
    main.SESSION.load({"BizSpeechComponent": []})
    main.app.dependency_overrides[main.get_client] = lambda: _BoomClient()
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        r = client.post("/chat", json={"message": "hi"})
        assert r.status_code == 502
        body = r.json()
        assert body["error"]["message"]              # message present
        assert "provider exploded" in body["error"]["message"]
    finally:
        main.app.dependency_overrides.clear()


def test_httpexception_passes_through():
    client = TestClient(main.app, raise_server_exceptions=False)
    main.SESSION.__init__()                          # unloaded → 503
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 503
