import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import main
from main import app, get_client
from llm.base import FakeLLMClient, LLMResponse, ToolCall

_REAL = Path(__file__).resolve().parent / "fixtures" / "sample_export.json"
_client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_session():
    # After conftest resets REGISTRY, get/create session for the shared client.
    # Mint a tbid first by making a request.
    _client.get("/health")
    tbid = _client.cookies.get("tbid")
    if tbid:
        s = main.REGISTRY.store(tbid).active()
        s._stack = []
        s._idx = -1
        s.pending = None
        s.transcript = []
        s.load(json.loads(_REAL.read_text(encoding="utf-8")))
    yield
    main.app.dependency_overrides.clear()


def test_chat_apply_undo(monkeypatch):
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="apply_mods",
                    arguments={"mods_yaml": "- op: set-speech-id\n  value: 999\n"})]),
        LLMResponse(text=None, tool_calls=[]),  # Fix-loop round 1 triggered
        LLMResponse(text=None, tool_calls=[]),  # Fix-loop round 2 triggered
        LLMResponse(text="Proposed.", tool_calls=[]),  # Turn ends
    ])
    app.dependency_overrides[get_client] = lambda: fake
    r = _client.post("/chat", json={"message": "set speech id to 999"})
    assert r.status_code == 200 and r.json()["proposal"] is not None
    assert _client.post("/apply").json()["applied"] is True
    assert _client.post("/undo").json()["ok"] is True


def test_apply_without_pending_returns_409():
    """After undo clears pending, /apply should return 409."""
    tbid = _client.cookies.get("tbid")
    main.REGISTRY.store(tbid).active().pending = None
    r = _client.post("/apply")
    assert r.status_code == 409


def test_summary_before_session_returns_503():
    """GET /summary before any /session upload returns 503."""
    tbid = _client.cookies.get("tbid")
    s = main.REGISTRY.store(tbid).active()
    s._stack = []
    s._idx = -1
    s.pending = None
    r = _client.get("/summary")
    assert r.status_code == 503


def test_findings_before_session_returns_503():
    """GET /findings before any /session upload returns 503."""
    tbid = _client.cookies.get("tbid")
    s = main.REGISTRY.store(tbid).active()
    s._stack = []
    s._idx = -1
    r = _client.get("/findings")
    assert r.status_code == 503
