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
