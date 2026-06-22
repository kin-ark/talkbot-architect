import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from main import app, get_client
from llm.base import FakeLLMClient, LLMResponse, ToolCall

_REAL = Path(__file__).resolve().parents[3] / "speech2572824560161596380.unpacked.json"
client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_session():
    main.SESSION._stack = []
    main.SESSION._idx = -1
    main.SESSION.pending = None
    main.SESSION.transcript = []
    yield
    main.app.dependency_overrides.clear()


def test_e2e_upload_edit_apply_export():
    files = {"file": ("speech.json", _REAL.read_bytes(), "application/json")}
    assert client.post("/session", files=files).status_code == 200
    before = client.get("/findings").json()
    err_before = sum(f["severity"] == "error" for f in before)

    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="apply_mods",
                    arguments={"mods_yaml": "- op: set-speech-id\n  value: 424242\n"})]),
        LLMResponse(text="Proposed setting speechId to 424242.", tool_calls=[]),
    ])
    app.dependency_overrides[get_client] = lambda: fake
    chat = client.post("/chat", json={"message": "set the speech id to 424242"}).json()
    assert chat["proposal"] is not None
    applied = client.post("/apply").json()
    assert applied["applied"] is True
    err_after = sum(f["severity"] == "error" for f in applied["findings"])
    assert err_after <= err_before  # no new errors introduced
    export = client.get("/export")
    assert json.loads(export.content)  # valid JSON round-trips
    app.dependency_overrides.clear()
