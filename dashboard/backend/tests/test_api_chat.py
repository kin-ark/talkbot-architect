import json
from pathlib import Path
from fastapi.testclient import TestClient
import main
from main import app, get_client
from llm.base import FakeLLMClient, LLMResponse, ToolCall

_REAL = Path(__file__).resolve().parents[3] / "speech2572824560161596380.unpacked.json"
client = TestClient(app)


def setup_function():
    main.SESSION.load(json.loads(_REAL.read_text(encoding="utf-8")))


def test_chat_apply_undo(monkeypatch):
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="apply_mods",
                    arguments={"mods_yaml": "- op: set-speech-id\n  value: 999\n"})]),
        LLMResponse(text="Proposed.", tool_calls=[]),
    ])
    app.dependency_overrides[get_client] = lambda: fake
    r = client.post("/chat", json={"message": "set speech id to 999"})
    assert r.status_code == 200 and r.json()["proposal"] is not None
    assert client.post("/apply").json()["applied"] is True
    assert client.post("/undo").json()["ok"] is True
    app.dependency_overrides.clear()


def test_apply_without_pending_returns_409():
    """After undo clears pending, /apply should return 409."""
    app.dependency_overrides.clear()
    main.SESSION.pending = None
    r = client.post("/apply")
    assert r.status_code == 409


def test_summary_before_session_returns_503():
    """GET /summary before any /session upload returns 503."""
    # Reset SESSION to a blank state
    main.SESSION._stack = []
    main.SESSION._idx = -1
    main.SESSION.pending = None
    r = client.get("/summary")
    assert r.status_code == 503


def test_findings_before_session_returns_503():
    """GET /findings before any /session upload returns 503."""
    main.SESSION._stack = []
    main.SESSION._idx = -1
    r = client.get("/findings")
    assert r.status_code == 503
