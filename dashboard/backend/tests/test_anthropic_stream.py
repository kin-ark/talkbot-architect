from llm.base import StreamChunk
from llm.anthropic_client import AnthropicClient


class _FakeTextDelta:
    def __init__(self, text):
        self.type = "text_delta"
        self.text = text


class _FakeEvent:
    def __init__(self, text):
        self.type = "content_block_delta"
        self.delta = _FakeTextDelta(text)


class _FakeFinalBlockText:
    type = "text"
    def __init__(self, t): self.text = t


class _FakeFinalMessage:
    def __init__(self): self.content = [_FakeFinalBlockText("hi there")]


class _FakeStreamCtx:
    def __enter__(self):
        class S:
            text_stream = iter([])
            def __iter__(self_inner): return iter([_FakeEvent("hi "), _FakeEvent("there")])
            def get_final_message(self_inner): return _FakeFinalMessage()
        self._s = S()
        return self._s
    def __exit__(self, *a): return False


def test_anthropic_stream_yields_deltas_then_final(monkeypatch):
    c = AnthropicClient.__new__(AnthropicClient)   # bypass __init__ (no SDK/key)
    c._model = "x"

    class _Msgs:
        def stream(self, **kw): return _FakeStreamCtx()

    class _Client:
        messages = _Msgs()

    c._client = _Client()
    chunks = list(c.stream_chat([], []))
    deltas = "".join(ch.text_delta for ch in chunks if ch.text_delta)
    finals = [ch.response for ch in chunks if ch.response]
    assert deltas == "hi there"
    assert len(finals) == 1
    assert finals[0].text == "hi there"
    assert isinstance(chunks[-1], StreamChunk) and chunks[-1].response is not None
