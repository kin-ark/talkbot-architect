from llm.anthropic_client import AnthropicClient
from llm.openai_client import OpenAIClient


def test_anthropic_is_retryable_classifies(monkeypatch):
    import anthropic
    assert AnthropicClient._is_retryable(anthropic.APIConnectionError(request=None)) is True
    # 5xx status error retryable, 4xx not
    class S(anthropic.APIStatusError):
        def __init__(self, code):
            self.status_code = code
    assert AnthropicClient._is_retryable(S(503)) is True
    assert AnthropicClient._is_retryable(S(400)) is False
    assert AnthropicClient._is_retryable(ValueError()) is False


def test_anthropic_chat_retries_then_succeeds(monkeypatch):
    c = AnthropicClient.__new__(AnthropicClient)
    c._model = "m"
    c.model = "m"
    c._thinking_budget = None
    c._attempts = 3
    c._sleep = lambda s: None
    import anthropic
    calls = {"n": 0}

    class _Msgs:
        def create(self, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise anthropic.APIConnectionError(request=None)

            class _Block:  # text block
                type = "text"
                text = "hi"

            class _R:
                content = [_Block()]
            return _R()
    c._client = type("X", (), {"messages": _Msgs()})()
    out = c.chat([], [])
    assert out.text == "hi" and calls["n"] == 3


def test_openai_is_retryable(monkeypatch):
    import openai
    assert OpenAIClient._is_retryable(openai.APIConnectionError(request=None)) is True
    assert OpenAIClient._is_retryable(ValueError()) is False
