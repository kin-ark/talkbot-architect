from llm.base import Message, ToolCall


def test_message_roundtrip_with_tool_calls():
    m = Message(role="assistant", content="hi",
                tool_calls=[ToolCall(id="t1", name="validate", arguments={"x": 1})])
    d = m.to_dict()
    assert isinstance(d, dict)
    m2 = Message.from_dict(d)
    assert m2.role == "assistant"
    assert m2.content == "hi"
    assert m2.tool_calls[0].id == "t1"
    assert m2.tool_calls[0].name == "validate"
    assert m2.tool_calls[0].arguments == {"x": 1}


def test_tool_message_roundtrip():
    m = Message(role="tool", content="{}", tool_call_id="t1")
    m2 = Message.from_dict(m.to_dict())
    assert m2.role == "tool"
    assert m2.tool_call_id == "t1"
    assert m2.tool_calls == []
