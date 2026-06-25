from fastapi.testclient import TestClient
from llm.base import Message, ToolCall
import main


def test_get_session_empty_when_no_session():
    main.SESSION._stack = []           # simulate no session loaded
    main.SESSION._idx = -1
    main.SESSION.transcript = []
    with TestClient(main.app) as client:
        r = client.get("/session")
    assert r.status_code == 200
    assert r.json()["summary"] is None


def test_get_session_returns_state_and_reconstructed_transcript():
    main.SESSION.load({"BizSpeechComponent": []})
    main.SESSION.transcript = [
        Message(role="user", content="add a node"),
        Message(role="assistant", content=None, tool_calls=[ToolCall("c1", "validate", {})]),
        Message(role="tool", tool_call_id="c1", content="{}"),
        Message(role="assistant", content="Done — added it."),
    ]
    with TestClient(main.app) as client:
        body = client.get("/session").json()
    assert body["summary"] is not None
    assert "findings" in body
    assert body["can_undo"] is False        # fresh load, single version
    assert body["transcript"] == [
        {"role": "user", "text": "add a node"},
        {"role": "agent", "text": "Done — added it."},
    ]


def test_reconstruct_transcript_helper():
    msgs = [
        Message(role="user", content="hi"),
        Message(role="assistant", content=""),            # empty → skipped
        Message(role="tool", tool_call_id="t", content="x"),  # tool → skipped
        Message(role="agent" if False else "assistant", content="ok"),
    ]
    assert main._reconstruct_transcript(msgs) == [
        {"role": "user", "text": "hi"},
        {"role": "agent", "text": "ok"},
    ]
