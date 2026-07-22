from orchestrator import _compact_for_send, _TOOL_STUB_MAX_CHARS
from llm.base import Message, ToolCall


def _big(n):
    return "x" * (_TOOL_STUB_MAX_CHARS + n)


def test_stubs_old_large_tool_results_only():
    big = _big(500)
    transcript = [
        Message(role="user", content="turn1"),
        Message(role="assistant", content=None, tool_calls=[ToolCall(id="c1", name="summarize", arguments={})]),
        Message(role="tool", tool_call_id="c1", content=big),          # OLD + big -> stub
        Message(role="user", content="turn2"),
        Message(role="assistant", content="ok"),
        Message(role="user", content="turn3 (current)"),
    ]
    out = _compact_for_send(transcript)
    assert len(out) == len(transcript)
    assert out[2].role == "tool" and out[2].tool_call_id == "c1"
    assert "_compacted" in out[2].content and big not in out[2].content
    # user/assistant untouched; input not mutated
    assert out[0].content == "turn1" and out[4].content == "ok"
    assert transcript[2].content == big   # original unchanged


def test_recent_and_small_tool_results_kept():
    small = "tiny result"
    transcript = [
        Message(role="user", content="t1"),
        Message(role="tool", tool_call_id="c1", content=small),        # small -> kept
        Message(role="user", content="t2"),
        Message(role="assistant", content=None, tool_calls=[ToolCall(id="c2", name="summarize", arguments={})]),
        Message(role="tool", tool_call_id="c2", content=_big(100)),    # recent (within last 2 turns) -> kept
        Message(role="user", content="t3"),
    ]
    out = _compact_for_send(transcript)
    assert out[1].content == small
    assert "_compacted" not in (out[4].content or "")


def test_short_history_unchanged():
    transcript = [Message(role="user", content="t1"),
                  Message(role="tool", tool_call_id="c1", content=_big(0))]
    out = _compact_for_send(transcript)
    assert out[1].content == transcript[1].content   # < KEEP_RECENT_TURNS -> untouched
