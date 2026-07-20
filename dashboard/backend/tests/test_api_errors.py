from fastapi.testclient import TestClient
from llm.base import LLMClient
import main


class _BoomClient(LLMClient):
    # subclass LLMClient so it inherits the default stream_chat (run_turn drives
    # the client via stream_chat); the raising chat still surfaces the error.
    def chat(self, messages, tools):
        raise RuntimeError("provider exploded")


def test_unhandled_exception_returns_error_shape():
    main.app.dependency_overrides[main.get_client] = lambda: _BoomClient()
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        client.get("/health")  # mint tbid
        tbid = client.cookies["tbid"]
        main.REGISTRY.store(tbid).active().load({"BizSpeechComponent": []})
        r = client.post("/chat", json={"message": "hi"})
        assert r.status_code == 502
        body = r.json()
        assert body["error"]["message"]              # message present
        assert "provider exploded" in body["error"]["message"]
    finally:
        main.app.dependency_overrides.clear()


def test_httpexception_passes_through():
    client = TestClient(main.app, raise_server_exceptions=False)
    # empty stack → 503 (no session loaded)
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 503


def test_unhandled_500_does_not_leak_exception_text():
    import asyncio, json as _json

    class _Req:
        class url:
            path = "/x"

    resp = asyncio.run(main._unhandled(_Req(), ValueError("secret /etc/passwd detail")))
    assert resp.status_code == 500
    blob = _json.dumps(_json.loads(bytes(resp.body)))
    assert "secret" not in blob and "/etc/passwd" not in blob
