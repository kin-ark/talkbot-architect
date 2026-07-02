import orchestrator
from llm.base import FakeLLMClient, LLMResponse
from session import Session


def _load(s):
    s.load({"BizSpeechComponent": "[]"})


def test_stream_emits_thinking_event_and_carries_blocks():
    s = Session()
    _load(s)
    fake = FakeLLMClient(script=[LLMResponse(text="done")], thinking=["thinking hard"])
    events = list(orchestrator.run_turn_stream(fake, s, "hi"))
    assert any(e["type"] == "thinking" and e["delta"] == "thinking hard" for e in events)
    # assistant transcript message carries the thinking blocks
    asst = [m for m in s.transcript if m.role == "assistant"][-1]
    assert asst.thinking_blocks and asst.thinking_blocks[0]["thinking"] == "thinking hard"
