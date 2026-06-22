"""Runtime LLM configuration store.

Holds in-memory overrides for provider/model/base_url/api_key.
The api_key is NEVER persisted, logged, or returned in any response —
only a boolean ``key_set`` is ever exposed to callers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class RuntimeConfig:
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None  # in-memory only; never persisted/logged/returned


# Module-global singleton — imported by main.py and tests.
CONFIG = RuntimeConfig()


def effective_key_set(provider: str | None) -> bool:
    """Return True if an API key is available for the resolved provider.

    Checks CONFIG.api_key first, then the relevant provider env var.
    """
    if CONFIG.api_key:
        return True
    resolved = (provider or os.environ.get("LLM_PROVIDER") or "anthropic").lower()
    if resolved == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if resolved in ("openai", "openai-compatible"):
        return bool(os.environ.get("OPENAI_API_KEY"))
    return False


def any_override() -> bool:
    """Return True if any CONFIG field is non-None/non-empty."""
    return any([CONFIG.provider, CONFIG.model, CONFIG.base_url, CONFIG.api_key])
