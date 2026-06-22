from __future__ import annotations

import os

from llm.base import LLMClient


class LLMConfigError(ValueError):
    pass


# Module-level references to client classes, exposed so tests can monkeypatch
# them without touching real SDK imports.
_anthropic_client_class = None  # lazily set inside make_client
_openai_client_class = None     # lazily set inside make_client


def make_client(
    provider: str | None,
    api_key: str | None,
    model: str | None,
    base_url: str | None = None,
) -> LLMClient:
    """Build and return an LLMClient for the given provider.

    Provider mapping
    ----------------
    ``anthropic``          → AnthropicClient; env key ANTHROPIC_API_KEY,
                             env base ANTHROPIC_BASE_URL.
    ``openai``             → OpenAIClient; env key OPENAI_API_KEY,
                             env base OPENAI_BASE_URL.
    ``openai-compatible``  → OpenAIClient, but *requires* a base_url (either
                             passed explicitly or via OPENAI_BASE_URL env var);
                             uses OPENAI_API_KEY as the env key.  This alias
                             exists to make LiteLLM/Ollama/gateway endpoints
                             explicit in config.

    ``base_url`` arg takes precedence; if None the function falls back to the
    per-provider ``*_BASE_URL`` env var.
    """
    global _anthropic_client_class, _openai_client_class  # noqa: PLW0603

    resolved_provider = (provider or os.environ.get("LLM_PROVIDER") or "anthropic").lower()

    if resolved_provider == "anthropic":
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMConfigError("ANTHROPIC_API_KEY not set")
        effective_base = base_url or os.environ.get("ANTHROPIC_BASE_URL")
        # Use monkeypatchable reference when set, else real class
        cls = _anthropic_client_class
        if cls is None:
            from llm.anthropic_client import AnthropicClient
            cls = AnthropicClient
        return cls(api_key=key, model=model or "claude-opus-4-8", base_url=effective_base)

    if resolved_provider in ("openai", "openai-compatible"):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise LLMConfigError("OPENAI_API_KEY not set")
        effective_base = base_url or os.environ.get("OPENAI_BASE_URL")
        if resolved_provider == "openai-compatible" and not effective_base:
            raise LLMConfigError(
                "base_url is required for provider 'openai-compatible' "
                "(set OPENAI_BASE_URL or pass base_url)"
            )
        cls = _openai_client_class
        if cls is None:
            from llm.openai_client import OpenAIClient
            cls = OpenAIClient
        return cls(api_key=key, model=model or "gpt-4o", base_url=effective_base)

    raise LLMConfigError(f"unknown provider {resolved_provider!r}")
