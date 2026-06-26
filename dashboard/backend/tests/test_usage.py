from llm.base import FakeLLMClient, LLMResponse, ToolCall
from session import Session
from orchestrator import run_turn_stream


def _load(s): s.load({"BizSpeechComponent": "[]"})


def test_usage_accumulates_and_emits_event():
    s = Session()
    _load(s)
    fake = FakeLLMClient(script=[LLMResponse(text="hi", tool_calls=[])],
                         usage=[{"input_tokens": 11, "output_tokens": 4}])
    fake.model = "claude-test"
    events = list(run_turn_stream(fake, s, "hello"))
    usage_evs = [e for e in events if e["type"] == "usage"]
    assert len(usage_evs) == 1
    assert usage_evs[0]["input_tokens"] == 11 and usage_evs[0]["output_tokens"] == 4
    assert usage_evs[0]["model"] == "claude-test"
    # accumulates on the session
    assert s.usage["input_tokens"] == 11 and s.usage["turns"] == 1
    # order: usage before done
    assert [e["type"] for e in events][-2:] == ["usage", "done"]
