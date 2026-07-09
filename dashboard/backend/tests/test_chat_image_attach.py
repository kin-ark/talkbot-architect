import base64
import io


_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def _client_with_session():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    c.post("/session/blank")
    return c


def test_image_media_type_detects_png():
    from main import _image_media_type
    assert _image_media_type("shot.png", _PNG) == "image/png"
    assert _image_media_type("note.txt", b"hello") is None


def test_attach_image_appends_to_images_not_attachment():
    c = _client_with_session()
    r = c.post("/chat/attach", files={"file": ("shot.png", _PNG, "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "image" and body["count"] == 1


def test_attach_two_images_counts_two():
    c = _client_with_session()
    c.post("/chat/attach", files={"file": ("a.png", _PNG, "image/png")})
    r = c.post("/chat/attach", files={"file": ("b.png", _PNG, "image/png")})
    assert r.json()["count"] == 2


def test_fifth_image_rejected():
    c = _client_with_session()
    for i in range(4):
        c.post("/chat/attach", files={"file": (f"{i}.png", _PNG, "image/png")})
    r = c.post("/chat/attach", files={"file": ("x.png", _PNG, "image/png")})
    assert r.status_code in (400, 413)


def test_delete_one_image_by_index():
    c = _client_with_session()
    c.post("/chat/attach", files={"file": ("a.png", _PNG, "image/png")})
    c.post("/chat/attach", files={"file": ("b.png", _PNG, "image/png")})
    r = c.request("DELETE", "/chat/attach", params={"kind": "image", "index": 0})
    assert r.status_code == 200
    # one left
    r2 = c.post("/chat/attach", files={"file": ("c.png", _PNG, "image/png")})
    assert r2.json()["count"] == 2


def test_xlsx_attach_still_single_attachment():
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Note"])
    ws.append(["Intent", "Type", "Content", "Language"])
    ws.append(["Positive", "Keyword", "ya", "Bahasa Indonesia"])
    buf = io.BytesIO()
    wb.save(buf)
    c = _client_with_session()
    r = c.post("/chat/attach", files={"file": ("intents.xls", buf.getvalue(),
               "application/vnd.ms-excel")})
    assert r.json()["kind"] == "intent-xlsx"     # unchanged single-attachment path


def test_model_is_vision_helper():
    import config_store
    import main
    cfg = config_store.RuntimeConfig()
    cfg.model_id = "claude-opus-4-8"
    assert main._model_is_vision(cfg) is True
    cfg.model_id = "__custom__"
    cfg.custom_vision = False
    assert main._model_is_vision(cfg) is False
    cfg.custom_vision = True
    assert main._model_is_vision(cfg) is True


def test_images_blocked_on_non_vision_model(monkeypatch):
    import config_store
    import main

    class _FakeClient:
        def __init__(self):
            self.model = "gpt-x-text"

        def stream_chat(self, messages, tools):
            from llm.base import LLMResponse
            yield type('Chunk', (), {
                'thinking_delta': None, 'text_delta': None, 'response': None, 'usage': None})()
            yield type('Chunk', (), {
                'thinking_delta': None, 'text_delta': None,
                'response': LLMResponse(text="hi", tool_calls=[]), 'usage': None})()

    class _FakeSession:
        _stack = [object()]

        class _Lock:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        _lock = _Lock()
        cancel_requested = False

        def __init__(self):
            self.images = [{"name": "a.png", "media_type": "image/png", "data": "fake"}]
            self.transcript = []
            self.pending = None
            self.attachment = None
            self.usage = {"input_tokens": 0, "output_tokens": 0, "turns": 0}

        def _autosave(self):
            pass

        def current(self):
            return {}

    cid = "test-cid-vision-block"
    cfg = config_store.config_for(cid)
    cfg.model_id = "__custom__"
    cfg.provider = "openai"
    cfg.model = "gpt-x-text"
    cfg.custom_vision = False
    cfg.api_key = "sk-x"

    main.app.dependency_overrides[main.get_client] = lambda: _FakeClient()
    main.app.dependency_overrides[main.current_session] = lambda: _FakeSession()
    main.app.dependency_overrides[main.client_id] = lambda: cid

    try:
        from fastapi.testclient import TestClient
        c = TestClient(main.app)
        r = c.post("/chat", json={"message": "look"})
        assert r.status_code == 400
        assert "image" in r.json().get("detail", "").lower()
    finally:
        main.app.dependency_overrides.clear()
