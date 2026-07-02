import pytest
from llm.factory import make_client, LLMConfigError


def test_missing_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(LLMConfigError):
        make_client(provider="anthropic", api_key=None, model=None)


def test_unknown_provider_raises():
    with pytest.raises(LLMConfigError):
        make_client(provider="nope", api_key="k", model=None)


# ---------------------------------------------------------------------------
# base_url threading tests
# ---------------------------------------------------------------------------

def test_openai_base_url_passed_through(monkeypatch):
    """make_client passes base_url through to OpenAIClient."""
    captured = {}

    class FakeOpenAIClient:
        def __init__(self, api_key, model, base_url=None, attempts=3, sleep=None):
            captured["base_url"] = base_url
            captured["api_key"] = api_key
            captured["model"] = model

    monkeypatch.setattr("llm.factory._openai_client_class", FakeOpenAIClient)
    make_client("openai", "k", "m", base_url="http://x")
    assert captured["base_url"] == "http://x"


def test_anthropic_base_url_passed_through(monkeypatch):
    """make_client passes base_url through to AnthropicClient."""
    captured = {}

    class FakeAnthropicClient:
        def __init__(self, api_key, model, base_url=None, thinking_budget=None):
            captured["base_url"] = base_url
            captured["api_key"] = api_key

    monkeypatch.setattr("llm.factory._anthropic_client_class", FakeAnthropicClient)
    make_client("anthropic", "k", "m", base_url="http://a")
    assert captured["base_url"] == "http://a"


def test_openai_env_base_url_fallback(monkeypatch):
    """When base_url arg is None, factory reads OPENAI_BASE_URL from env."""
    captured = {}

    class FakeOpenAIClient:
        def __init__(self, api_key, model, base_url=None, attempts=3, sleep=None):
            captured["base_url"] = base_url

    monkeypatch.setenv("OPENAI_BASE_URL", "http://from-env")
    monkeypatch.setattr("llm.factory._openai_client_class", FakeOpenAIClient)
    make_client("openai", "k", "m", base_url=None)
    assert captured["base_url"] == "http://from-env"


def test_anthropic_env_base_url_fallback(monkeypatch):
    """When base_url arg is None, factory reads ANTHROPIC_BASE_URL from env."""
    captured = {}

    class FakeAnthropicClient:
        def __init__(self, api_key, model, base_url=None, thinking_budget=None):
            captured["base_url"] = base_url

    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://from-env-a")
    monkeypatch.setattr("llm.factory._anthropic_client_class", FakeAnthropicClient)
    make_client("anthropic", "k", "m", base_url=None)
    assert captured["base_url"] == "http://from-env-a"


def test_openai_compatible_provider_uses_openai_client(monkeypatch):
    """Provider 'openai-compatible' routes to OpenAIClient and requires base_url."""
    captured = {}

    class FakeOpenAIClient:
        def __init__(self, api_key, model, base_url=None, attempts=3, sleep=None):
            captured["base_url"] = base_url
            captured["model"] = model

    monkeypatch.setattr("llm.factory._openai_client_class", FakeOpenAIClient)
    make_client("openai-compatible", "k", "m", base_url="http://compat")
    assert captured["base_url"] == "http://compat"


def test_openai_compatible_without_base_url_raises(monkeypatch):
    """Provider 'openai-compatible' without base_url raises LLMConfigError."""
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    class FakeOpenAIClient:
        def __init__(self, api_key, model, base_url=None, attempts=3, sleep=None):
            pass

    monkeypatch.setattr("llm.factory._openai_client_class", FakeOpenAIClient)
    with pytest.raises(LLMConfigError):
        make_client("openai-compatible", "k", "m", base_url=None)
