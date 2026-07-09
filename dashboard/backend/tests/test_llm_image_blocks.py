from llm.base import Message


def _img_msg():
    return [Message(role="user", content="what is this?",
                    images=[{"media_type": "image/png", "data": "AAAABBBB"}])]


def test_anthropic_user_image_blocks():
    from llm.anthropic_client import AnthropicClient
    out = AnthropicClient._to_anthropic_messages(_img_msg())
    assert len(out) == 1
    content = out[0]["content"]
    assert isinstance(content, list)
    img = content[0]
    assert img["type"] == "image"
    assert img["source"] == {"type": "base64", "media_type": "image/png", "data": "AAAABBBB"}
    # text block after the image(s)
    assert content[-1] == {"type": "text", "text": "what is this?"}


def test_anthropic_text_only_unchanged():
    from llm.anthropic_client import AnthropicClient
    out = AnthropicClient._to_anthropic_messages([Message(role="user", content="hi")])
    assert out[0]["content"] == "hi"          # plain string preserved


def test_anthropic_image_only_no_text_block():
    from llm.anthropic_client import AnthropicClient
    out = AnthropicClient._to_anthropic_messages(
        [Message(role="user", content=None, images=[{"media_type": "image/jpeg", "data": "X"}])])
    content = out[0]["content"]
    assert len(content) == 1 and content[0]["type"] == "image"


def test_openai_user_image_blocks():
    from llm.openai_client import OpenAIClient
    out = OpenAIClient._to_openai_messages(_img_msg())
    content = out[0]["content"]
    assert isinstance(content, list)
    assert content[0] == {"type": "image_url",
                          "image_url": {"url": "data:image/png;base64,AAAABBBB"}}
    assert content[-1] == {"type": "text", "text": "what is this?"}


def test_openai_text_only_unchanged():
    from llm.openai_client import OpenAIClient
    out = OpenAIClient._to_openai_messages([Message(role="user", content="hi")])
    assert out[0]["content"] == "hi"
