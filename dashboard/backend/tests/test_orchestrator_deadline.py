"""run_turn_stream stops a too-long turn with stop_reason=timeout."""
import orchestrator
from session import Session
from llm.base import FakeLLMClient, LLMResponse, ToolCall


def _load(s):
    s.load({"BizSpeechComponent": "[]"})


def test_turn_deadline_stops_with_timeout(monkeypatch):
    monkeypatch.setattr(orchestrator, "_TURN_DEADLINE_S", 0)   # deadline already passed
    s = Session()
    _load(s)
    # A tool-calling script that would otherwise loop; the deadline fires first.
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="t1", name="validate", arguments={})]),
        LLMResponse(text="done", tool_calls=[]),
    ])
    events = list(orchestrator.run_turn_stream(fake, s, "hi"))
    done = [e for e in events if e["type"] == "done"]
    assert done and done[-1]["stop_reason"] == "timeout"
