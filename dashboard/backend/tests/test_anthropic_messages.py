"""Regression: Anthropic requires the tool_results answering one assistant turn
to live in a SINGLE user message, one block per tool_use id. Multiple tool calls
in one response must NOT become multiple user messages, and a reused tool_use id
must not produce duplicate tool_result blocks (the cause of
'each tool_use must have a single result' 400s)."""
from llm.anthropic_client import AnthropicClient
from llm.base import Message, ToolCall


def test_multiple_tool_results_coalesce_into_one_user_message():
    msgs = [
        Message(role="user", content="hi"),
        Message(role="assistant", content=None, tool_calls=[
            ToolCall("A", "validate", {}), ToolCall("B", "summarize", {})]),
        Message(role="tool", tool_call_id="A", content="{}"),
        Message(role="tool", tool_call_id="B", content="{}"),
    ]
    out = AnthropicClient._to_anthropic_messages(msgs)
    # user, assistant(2 tool_use), user(2 tool_result) — exactly 3 messages
    assert len(out) == 3
    assistant = out[1]
    assert [b["type"] for b in assistant["content"]] == ["tool_use", "tool_use"]
    results = out[2]
    assert results["role"] == "user"
    ids = [b["tool_use_id"] for b in results["content"] if b["type"] == "tool_result"]
    assert ids == ["A", "B"]            # both results, one message


def test_duplicate_tool_use_id_is_deduped():
    msgs = [
        Message(role="assistant", content=None, tool_calls=[
            ToolCall("X", "validate", {}), ToolCall("X", "validate", {})]),
        Message(role="tool", tool_call_id="X", content="{}"),
        Message(role="tool", tool_call_id="X", content="{}"),
    ]
    out = AnthropicClient._to_anthropic_messages(msgs)
    tool_use = [b for b in out[0]["content"] if b["type"] == "tool_use"]
    tool_result = [b for b in out[1]["content"] if b["type"] == "tool_result"]
    assert len(tool_use) == 1           # deduped tool_use
    assert len(tool_result) == 1        # single result for id X
