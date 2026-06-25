from llm.base import FakeLLMClient, LLMResponse, ToolCall
from session import Session
from orchestrator import run_turn_stream, run_turn


def _load(s):
    s.load({"BizSpeechComponent": "[]"})


def test_stream_emits_tokens_tool_and_done():
    s = Session(); _load(s)
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="validate", arguments={})]),
        LLMResponse(text="all good", tool_calls=[]),
    ])
    events = list(run_turn_stream(fake, s, "check"))
    types = [e["type"] for e in events]
    assert types[0] == "tool_start" and types[1] == "tool_result"
    assert "token" in types
    assert events[-1]["type"] == "done"
    assert events[-1]["canceled"] is False
    assert events[-1]["text"] == "all good"


def test_stream_emits_proposal():
    s = Session(); s.load({"BizSpeechId": "OLD-123"})
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="apply_mods",
                    arguments={"mods_yaml": "- op: set-speech-id\n  speech_id: NEW-456\n"})]),
        LLMResponse(text="done", tool_calls=[]),
    ])
    events = list(run_turn_stream(fake, s, "rename"))
    props = [e for e in events if e["type"] == "proposal"]
    assert len(props) == 1
    assert props[0]["proposal"]["diff"] or props[0]["proposal"]["checker_delta"] is not None
    assert s.pending is not None


def test_stream_cancel_rolls_back():
    s = Session(); _load(s)
    s.cancel_requested = True
    fake = FakeLLMClient([LLMResponse(text=None, tool_calls=[ToolCall("t1", "validate", {})])])
    before = len(s.transcript)
    events = list(run_turn_stream(fake, s, "hi"))
    assert events[-1] == {"type": "done", "canceled": True, "text": ""}
    assert len(s.transcript) == before
    assert s.cancel_requested is False


def test_run_turn_still_works_via_drainer():
    s = Session(); _load(s)
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="validate", arguments={})]),
        LLMResponse(text="No errors found.", tool_calls=[]),
    ])
    out = run_turn(fake, s, "check it")
    assert out["text"] == "No errors found."
    assert out["tool_trace"][0]["name"] == "validate"
    assert out["canceled"] is False
