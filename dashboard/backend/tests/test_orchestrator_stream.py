from llm.base import FakeLLMClient, LLMResponse, ToolCall
from session import Session
from orchestrator import run_turn_stream, run_turn, _MAX_FIX_BACKSTOPS


def _load(s):
    s.load({"BizSpeechComponent": "[]"})


def test_stream_emits_tokens_tool_and_done():
    s = Session()
    _load(s)
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
    # set-speech-id on minimal data succeeds but the proposed_data may still have
    # checker findings (pre-existing errors on a minimal doc), which triggers the
    # fix-loop backstop. Supply enough script items to survive it.
    s = Session()
    s.load({"BizSpeechComponent": [], "BizSpeechScene": "null"})
    apply_call = ToolCall(id="t1", name="apply_mods",
                          arguments={"mods_yaml": "- op: set-speech-id\n  value: 456\n"})
    script = [
        LLMResponse(text=None, tool_calls=[apply_call]),
        *[LLMResponse(text="done", tool_calls=[]) for _ in range(_MAX_FIX_BACKSTOPS + 1)],
    ]
    events = list(run_turn_stream(FakeLLMClient(script=script), s, "rename"))
    props = [e for e in events if e["type"] == "proposal"]
    assert len(props) >= 1
    assert props[0]["proposal"]["diff"] or props[0]["proposal"]["checker_delta"] is not None
    assert s.pending is not None


def test_stream_cancel_rolls_back():
    s = Session()
    _load(s)
    s.cancel_requested = True
    fake = FakeLLMClient([LLMResponse(text=None, tool_calls=[ToolCall("t1", "validate", {})])])
    before = len(s.transcript)
    events = list(run_turn_stream(fake, s, "hi"))
    assert events[-1] == {"type": "done", "canceled": True, "text": ""}
    assert len(s.transcript) == before
    assert s.cancel_requested is False


def test_run_turn_still_works_via_drainer():
    s = Session()
    _load(s)
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="validate", arguments={})]),
        LLMResponse(text="No errors found.", tool_calls=[]),
    ])
    out = run_turn(fake, s, "check it")
    assert out["text"] == "No errors found."
    assert out["tool_trace"][0]["name"] == "validate"
    assert out["canceled"] is False


def test_run_turn_stream_emits_status_event():
    from llm.base import LLMResponse
    class _C:
        model = "x"
        def stream_chat(self, messages, tools):
            from llm.base import StreamChunk
            yield StreamChunk(status={"kind": "retrying", "attempt": 1, "attempts": 3, "wait": 1.0})
            yield StreamChunk(response=LLMResponse(text="ok", tool_calls=[]), usage={"input_tokens": 1, "output_tokens": 1})
    s = Session()
    s.load({"BizSpeechComponent": "[]"})
    evs = list(run_turn_stream(_C(), s, "hi"))
    assert any(e.get("type") == "status" and e.get("kind") == "retrying" for e in evs)
