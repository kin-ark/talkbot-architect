"""Tests for orchestrator.py (Task 15).

TDD RED phase: tests written before implementation.
"""
from llm.base import FakeLLMClient, LLMResponse, ToolCall
from session import Session
from orchestrator import run_turn, _MAX_FIX_BACKSTOPS


def test_run_turn_executes_tool_then_returns_text():
    session = Session()
    session.load({"BizSpeechComponent": "[]"})
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="validate", arguments={})]),
        LLMResponse(text="No errors found.", tool_calls=[]),
    ])
    out = run_turn(fake, session, "check it")
    assert out["text"] == "No errors found."
    assert out["tool_trace"][0]["name"] == "validate"


def test_run_turn_surfaces_proposal():
    # set-speech-id on minimal data succeeds but the proposed_data may still have
    # checker findings (pre-existing warnings/errors on a minimal doc), which
    # triggers the fix-loop backstop. Supply enough script items to survive it.
    session = Session()
    session.load({"BizSpeechComponent": [], "BizSpeechScene": "null"})
    apply_call = ToolCall(id="t1", name="apply_mods",
                          arguments={"mods_yaml": "- op: set-speech-id\n  value: 456\n"})
    # 1st: apply_mods → proposal (may have pre-existing findings → backstop)
    # 2nd: backstop round LLM text-only (if backstop fires up to _MAX_FIX_BACKSTOPS times)
    # then final text reply
    script = [
        LLMResponse(text=None, tool_calls=[apply_call]),
        *[LLMResponse(text="Proposed a change.", tool_calls=[]) for _ in range(_MAX_FIX_BACKSTOPS + 1)],
    ]
    fake = FakeLLMClient(script=script)
    out = run_turn(fake, session, "rename speech id")
    assert session.pending is not None
    assert out["proposal"]["checker_delta"] is not None or out["proposal"]["diff"]
