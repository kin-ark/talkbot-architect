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
