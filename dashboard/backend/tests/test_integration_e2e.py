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
    # Mint a tbid by making a request, then reset session state
    client.get("/health")
    tbid = client.cookies.get("tbid")
    if tbid:
        s = main.REGISTRY.store(tbid).active()
        s._stack = []
        s._idx = -1
        s.pending = None
        s.transcript = []
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
    exported = json.loads(export.content)  # valid JSON round-trips
    assert exported
    # Assert the mod took effect: BizSpeechComponent is a JSON-encoded string
    # in wire format; decode it and verify every component carries speechId=424242.
    bsc_raw = exported.get("BizSpeechComponent")
    assert bsc_raw is not None, "BizSpeechComponent missing from export"
    bsc = json.loads(bsc_raw) if isinstance(bsc_raw, str) else bsc_raw
    assert isinstance(bsc, list) and len(bsc) > 0, "BizSpeechComponent is empty"
    for comp in bsc:
        assert comp.get("speechId") == 424242, (
            f"expected speechId=424242 in component, got {comp.get('speechId')!r}"
        )
    app.dependency_overrides.clear()
