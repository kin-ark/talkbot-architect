from llm.base import FakeLLMClient, LLMResponse, ToolCall
from session import Session
from orchestrator import run_turn


def _load(session):
    session.load({"BizSpeechComponent": []})


def test_cancel_before_turn_rolls_back_transcript():
    s = Session()
    _load(s)
    s.cancel_requested = True
    # Script would loop forever if not canceled; cancel must short-circuit.
    client = FakeLLMClient([LLMResponse(text=None, tool_calls=[ToolCall("t1", "validate", {})])])
    before = len(s.transcript)
    out = run_turn(client, s, "hello")
    assert out["canceled"] is True
    assert len(s.transcript) == before          # user msg rolled back
    assert s.cancel_requested is False           # flag cleared for next turn


def test_normal_turn_not_canceled():
    s = Session()
    _load(s)
    client = FakeLLMClient([LLMResponse(text="hi", tool_calls=[])])
    out = run_turn(client, s, "hello")
    assert out["canceled"] is False
    assert out["text"] == "hi"
