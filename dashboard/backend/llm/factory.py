from __future__ import annotations

import os

from llm.base import LLMClient


class LLMConfigError(ValueError):
    pass


def make_client(provider: str | None, api_key: str | None, model: str | None) -> LLMClient:
    provider = (provider or os.environ.get("LLM_PROVIDER") or "anthropic").lower()
    if provider == "anthropic":
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMConfigError("ANTHROPIC_API_KEY not set")
        from llm.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=key, model=model or "claude-opus-4-8")
    if provider == "openai":
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise LLMConfigError("OPENAI_API_KEY not set")
        from llm.openai_client import OpenAIClient
        return OpenAIClient(api_key=key, model=model or "gpt-4o")
    raise LLMConfigError(f"unknown provider {provider!r}")
