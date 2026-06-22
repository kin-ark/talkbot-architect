from llm.base import FakeLLMClient, LLMResponse, ToolCall, Message, ToolSpec


def test_fake_returns_scripted_responses_in_order():
    fake = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[ToolCall(id="1", name="validate", arguments={})]),
        LLMResponse(text="done", tool_calls=[]),
    ])
    r1 = fake.chat([Message(role="user", content="check it")], tools=[])
    assert r1.tool_calls[0].name == "validate"
    r2 = fake.chat([Message(role="user", content="x")], tools=[])
    assert r2.text == "done"
