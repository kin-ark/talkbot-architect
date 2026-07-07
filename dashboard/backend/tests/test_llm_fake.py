from llm.base import FakeLLMClient, LLMResponse, ToolCall, Message


def test_fake_returns_scripted_responses_in_order():
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="1", name="validate", arguments={})]),
        LLMResponse(text="done", tool_calls=[]),
    ])
    r1 = fake.chat([Message(role="user", content="check it")], tools=[])
    assert r1.tool_calls[0].name == "validate"
    r2 = fake.chat([Message(role="user", content="x")], tools=[])
    assert r2.text == "done"


def test_fake_stream_chat_yields_text_then_final_response():
    fake = FakeLLMClient(script=[LLMResponse(text="hello world", tool_calls=[])])
    chunks = list(fake.stream_chat([], []))
    deltas = [c.text_delta for c in chunks if c.text_delta is not None]
    finals = [c.response for c in chunks if c.response is not None]
    assert "".join(deltas) == "hello world"
    assert len(finals) == 1
    assert finals[0].text == "hello world"


def test_fake_stream_chat_final_carries_tool_calls():
    call = ToolCall(id="t1", name="validate", arguments={})
    fake = FakeLLMClient(script=[LLMResponse(text=None, tool_calls=[call])])
    chunks = list(fake.stream_chat([], []))
    finals = [c.response for c in chunks if c.response is not None]
    assert len(finals) == 1
    assert finals[0].tool_calls[0].name == "validate"
    assert [c for c in chunks if c.text_delta] == []   # no text → no deltas
