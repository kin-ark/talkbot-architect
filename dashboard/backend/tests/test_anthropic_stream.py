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


def test_anthropic_stream_yields_retry_status_then_succeeds(monkeypatch):
    import anthropic
    c = AnthropicClient.__new__(AnthropicClient)
    c._model = "x"
    c._attempts = 3
    slept = []
    c._sleep = lambda s: slept.append(s)
    calls = {"n": 0}

    class _Msgs:
        def stream(self, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                raise anthropic.APIConnectionError(request=None)  # retryable, pre-emit
            return _FakeStreamCtx()   # 2nd attempt streams "hi there"
    class _Client:
        messages = _Msgs()
    c._client = _Client()

    chunks = list(c.stream_chat([], []))
    status = [ch.status for ch in chunks if ch.status]
    assert status and status[0]["kind"] == "retrying"
    assert status[0]["attempt"] == 1 and status[0]["attempts"] == 3
    assert len(slept) == 1                      # slept once before the retry
    assert any(ch.response for ch in chunks)    # eventually succeeded


class _EmptyStreamCtx:
    """Opens a stream that yields no deltas and asserts on get_final_message
    (the SDK's signal that no complete message arrived) -> EmptyStreamError."""
    def __enter__(self):
        class S:
            text_stream = iter([])
            def __iter__(self_inner): return iter([])
            def get_final_message(self_inner): raise AssertionError("no snapshot")
        return S()
    def __exit__(self, *a): return False


def test_empty_stream_error_is_retryable():
    from llm.anthropic_client import EmptyStreamError
    assert AnthropicClient._is_retryable(EmptyStreamError("x")) is True


def test_anthropic_empty_stream_retries_then_succeeds():
    c = AnthropicClient.__new__(AnthropicClient)
    c._model = "x"
    c._attempts = 3
    slept = []
    c._sleep = lambda s: slept.append(s)
    calls = {"n": 0}

    class _Msgs:
        def stream(self, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                return _EmptyStreamCtx()   # empty -> EmptyStreamError, pre-emit -> retry
            return _FakeStreamCtx()        # 2nd attempt streams "hi there"
    class _Client:
        messages = _Msgs()
    c._client = _Client()

    chunks = list(c.stream_chat([], []))
    status = [ch.status for ch in chunks if ch.status]
    finals = [ch.response for ch in chunks if ch.response]
    assert status and status[0]["kind"] == "retrying"
    assert finals and finals[0].text == "hi there"
    assert calls["n"] == 2


def test_max_tokens_large_enough_for_full_manifest():
    """The output cap must be well above a full-bot manifest (old 4096 truncated
    the build tool input mid-JSON -> empty manifest_yaml)."""
    from llm.anthropic_client import _MAX_OUTPUT_TOKENS
    assert _MAX_OUTPUT_TOKENS >= 16000
    c = AnthropicClient.__new__(AnthropicClient)
    c._thinking_budget = 2048
    assert c._max_tokens() == 2048 + _MAX_OUTPUT_TOKENS
    c._thinking_budget = None
    assert c._max_tokens() == _MAX_OUTPUT_TOKENS
