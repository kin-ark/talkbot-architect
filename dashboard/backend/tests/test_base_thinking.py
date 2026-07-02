from llm.base import FakeLLMClient, LLMResponse, Message, StreamChunk


def test_message_thinking_blocks_roundtrip():
    m = Message(role="assistant", content="hi",
                thinking_blocks=[{"type": "thinking", "thinking": "hmm", "signature": "sig"}])
    d = m.to_dict()
    assert d["thinking_blocks"] == [{"type": "thinking", "thinking": "hmm", "signature": "sig"}]
    m2 = Message.from_dict(d)
    assert m2.thinking_blocks == m.thinking_blocks


def test_message_from_dict_defaults_thinking_blocks():
    m = Message.from_dict({"role": "assistant", "content": "x"})   # legacy transcript
    assert m.thinking_blocks == []


def test_stream_chunk_and_response_have_thinking_defaults():
    assert StreamChunk().thinking_delta is None
    assert LLMResponse(text="x").thinking_blocks == []


def test_fake_client_emits_thinking_when_scripted():
    fake = FakeLLMClient(script=[LLMResponse(text="hello")], thinking=["reasoning here"])
    chunks = list(fake.stream_chat([], []))
    assert any(c.thinking_delta for c in chunks)
    assert chunks[0].thinking_delta == "reasoning here"
    final = [c for c in chunks if c.response is not None][0]
    assert final.response.thinking_blocks and final.response.thinking_blocks[0]["type"] == "thinking"


def test_fake_client_no_thinking_by_default():
    fake = FakeLLMClient(script=[LLMResponse(text="hi there")])
    chunks = list(fake.stream_chat([], []))
    assert all(c.thinking_delta is None for c in chunks)
