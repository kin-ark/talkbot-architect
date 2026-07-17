from llm.anthropic_client import AnthropicClient
from llm.base import Message, ToolCall


def _client(budget):
    c = AnthropicClient.__new__(AnthropicClient)
    c._model = "m"
    c.model = "m"
    c._thinking_budget = budget
    c._attempts = 3
    c._sleep = lambda s: None
    return c


def test_max_tokens_and_thinking_arg():
    from llm.anthropic_client import _MAX_OUTPUT_TOKENS
    on = _client(2048)
    assert on._max_tokens() == 2048 + _MAX_OUTPUT_TOKENS
    assert on._thinking_arg() == {"type": "enabled", "budget_tokens": 2048}
    off = _client(None)
    assert off._max_tokens() == _MAX_OUTPUT_TOKENS and off._thinking_arg() is None


def test_to_anthropic_replays_thinking_before_tool_use():
    msgs = [Message(role="assistant", content="ok",
                    tool_calls=[ToolCall(id="t1", name="validate", arguments={})],
                    thinking_blocks=[{"type": "thinking", "thinking": "reason", "signature": "s"}])]
    out = AnthropicClient._to_anthropic_messages(msgs)
    content = out[0]["content"]
    assert content[0]["type"] == "thinking"
    assert content[1]["type"] == "text"
    assert content[2]["type"] == "tool_use"


def test_to_anthropic_no_thinking_unchanged():
    msgs = [Message(role="assistant", content="hi",
                    tool_calls=[ToolCall(id="t1", name="validate", arguments={})])]
    out = AnthropicClient._to_anthropic_messages(msgs)
    types = [b["type"] for b in out[0]["content"]]
    assert types == ["text", "tool_use"]


def test_stream_emits_thinking_delta_and_blocks():
    c = _client(2048)

    class _Delta:
        def __init__(self, t, **kw):
            self.type = t
            for k, v in kw.items():
                setattr(self, k, v)

    class _Event:
        def __init__(self, delta):
            self.type = "content_block_delta"
            self.delta = delta

    class _Block:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _Final:
        content = [_Block(type="thinking", thinking="deep", signature="sig"),
                   _Block(type="text", text="answer")]
        usage = type("U", (), {"input_tokens": 1, "output_tokens": 2})()

    class _Stream:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def __iter__(self):
            return iter([_Event(_Delta("thinking_delta", thinking="deep")),
                         _Event(_Delta("text_delta", text="answer"))])
        def get_final_message(self): return _Final()

    c._client = type("X", (), {"messages": type("M", (), {"stream": lambda self, **kw: _Stream()})()})()
    chunks = list(c.stream_chat([], []))
    assert any(ch.thinking_delta == "deep" for ch in chunks)
    final = [ch for ch in chunks if ch.response is not None][0]
    assert final.response.text == "answer"
    assert final.response.thinking_blocks[0]["thinking"] == "deep"
