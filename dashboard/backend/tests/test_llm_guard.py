import pytest

from llm.factory import LLMConfigError, make_client


def test_make_client_empty_model_raises():
    with pytest.raises(LLMConfigError):
        make_client(provider="anthropic", api_key="sk-test", model="", base_url=None)


def test_make_client_none_model_raises():
    with pytest.raises(LLMConfigError):
        make_client(provider="anthropic", api_key="sk-test", model=None, base_url=None)


def test_stream_error_before_message_start_is_clear(monkeypatch):
    # Simulate a stream that yields no message_start then asserts in
    # get_final_message() — must surface as a clear error, not AssertionError.
    from llm.anthropic_client import AnthropicClient
    from llm.base import Message

    class _FakeStream:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def __iter__(self): return iter([])          # no events
        def get_final_message(self):
            raise AssertionError("Never called `message_start`.")

    class _FakeMessages:
        def stream(self, **kw): return _FakeStream()

    c = AnthropicClient(api_key="k", model="deepseek-chat", attempts=1)
    c._client = type("X", (), {"messages": _FakeMessages()})()
    with pytest.raises(Exception) as ei:      # noqa: PT011
        list(c.stream_chat([Message(role="user", content="hi")], []))
    assert not isinstance(ei.value, AssertionError)
    assert "message" in str(ei.value).lower() or "model" in str(ei.value).lower()
