from types import SimpleNamespace
from llm.anthropic_client import AnthropicClient
from llm.openai_client import OpenAIClient


class _AStream:
    def __enter__(self):
        class S:
            def __iter__(self_): return iter([])
            def get_final_message(self_):
                return SimpleNamespace(content=[SimpleNamespace(type="text", text="hi")],
                                       usage=SimpleNamespace(input_tokens=9, output_tokens=3))
        return S()
    def __exit__(self, *a): return False


def test_anthropic_usage_on_final_chunk():
    c = AnthropicClient.__new__(AnthropicClient); c._model = "m"; c.model = "m"
    c._client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **k: _AStream()))
    chunks = list(c.stream_chat([], []))
    final = [ch for ch in chunks if ch.response][0]
    assert final.usage == {"input_tokens": 9, "output_tokens": 3}


def test_openai_usage_on_final_chunk():
    c = OpenAIClient.__new__(OpenAIClient); c._model = "m"; c.model = "m"
    def _create(**kw):
        assert kw.get("stream_options") == {"include_usage": True}
        return iter([
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="hi", tool_calls=None))], usage=None),
            SimpleNamespace(choices=[], usage=SimpleNamespace(prompt_tokens=7, completion_tokens=2)),
        ])
    c._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_create)))
    chunks = list(c.stream_chat([], []))
    final = [ch for ch in chunks if ch.response][0]
    assert final.usage == {"input_tokens": 7, "output_tokens": 2}
