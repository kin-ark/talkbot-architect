"""Request-size caps on /session upload and /chat message."""
from fastapi.testclient import TestClient
import main


def _client():
    c = TestClient(main.app)
    c.get("/health")
    return c


def test_upload_too_large_413(monkeypatch):
    monkeypatch.setattr(main, "_MAX_UPLOAD_BYTES", 1024)
    big = b"x" * 2048
    with _client() as c:
        r = c.post("/session", files={"file": ("big.json", big, "application/json")})
    assert r.status_code == 413


def test_chat_message_length_capped():
    """ChatRequest enforces the message cap (FastAPI 422s an over-cap body)."""
    import pydantic
    main.ChatRequest(message="x" * main._MAX_MESSAGE_CHARS)   # at cap: ok
    try:
        main.ChatRequest(message="x" * (main._MAX_MESSAGE_CHARS + 1))
    except pydantic.ValidationError:
        return
    raise AssertionError("over-cap message was not rejected")
