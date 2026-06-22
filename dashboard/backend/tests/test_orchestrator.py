"""Tests for orchestrator.py (Task 15).

TDD RED phase: tests written before implementation.
"""
from llm.base import FakeLLMClient, LLMResponse, ToolCall
from session import Session
from orchestrator import run_turn


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
    session = Session()
    session.load({"BizSpeechId": "OLD-123"})
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="apply_mods",
                    arguments={"mods_yaml": "- op: set-speech-id\n  speech_id: NEW-456\n"})]),
        LLMResponse(text="Proposed a change.", tool_calls=[]),
    ])
    out = run_turn(fake, session, "rename speech id")
    assert session.pending is not None
    assert out["proposal"]["checker_delta"] is not None or out["proposal"]["diff"]
