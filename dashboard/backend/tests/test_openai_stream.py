from types import SimpleNamespace
from llm.openai_client import OpenAIClient


def _delta_chunk(content=None, tool_calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(
        content=content, tool_calls=tool_calls))])


def _tc(index, cid=None, name=None, args=None):
    return SimpleNamespace(index=index, id=cid,
                           function=SimpleNamespace(name=name, arguments=args))


def test_openai_stream_text_and_tool_assembly():
    c = OpenAIClient.__new__(OpenAIClient)
    c._model = "x"

    def _create(**kw):
        return iter([
            _delta_chunk(content="hel"),
            _delta_chunk(content="lo"),
            _delta_chunk(tool_calls=[_tc(0, cid="t1", name="validate", args="{}")]),
        ])

    c._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_create)))
    chunks = list(c.stream_chat([], []))
    deltas = "".join(ch.text_delta for ch in chunks if ch.text_delta)
    final = [ch.response for ch in chunks if ch.response][0]
    assert deltas == "hello"
    assert final.text == "hello"
    assert final.tool_calls[0].name == "validate"
    assert final.tool_calls[0].id == "t1"


def test_openai_truncated_tool_args_degrade_not_crash():
    """A truncated/malformed streamed tool-arg fragment must not crash the turn;
    it degrades to empty args so the dispatch guard returns a clean error."""
    c = OpenAIClient.__new__(OpenAIClient)
    c._model = "x"

    def _create(**kw):
        return iter([
            # 'args' is truncated mid-JSON (invalid) — used to raise json.loads.
            _delta_chunk(tool_calls=[_tc(0, cid="t1", name="build", args='{"manifest_yaml": "abc')]),
        ])

    c._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_create)))
    chunks = list(c.stream_chat([], []))
    final = [ch.response for ch in chunks if ch.response][0]
    assert final.tool_calls[0].name == "build"
    assert final.tool_calls[0].arguments == {}   # degraded, not a crash


def test_openai_stream_yields_retry_status_then_succeeds():
    import openai
    c = OpenAIClient.__new__(OpenAIClient)
    c._model = "x"
    c._attempts = 3
    slept = []
    c._sleep = lambda s: slept.append(s)
    calls = {"n": 0}

    def _create(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise openai.APIConnectionError(request=None)  # retryable, pre-emit
        return iter([_delta_chunk(content="ok")])  # 2nd attempt

    c._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_create)))
    chunks = list(c.stream_chat([], []))
    status = [ch.status for ch in chunks if ch.status]
    assert status and status[0]["kind"] == "retrying"
    assert status[0]["attempt"] == 1 and status[0]["attempts"] == 3
    assert len(slept) == 1                      # slept once before the retry
    assert any(ch.response for ch in chunks)    # eventually succeeded
