"""Per-client runtime LLM configuration.

Each client (browser cookie id) gets its own RuntimeConfig. The api_key is
NEVER persisted, logged, or returned — only a boolean ``key_set`` is exposed.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None  # in-memory only; never persisted/logged/returned
    show_reasoning: bool = True


_CONFIGS: dict[str, RuntimeConfig] = {}
_lock = threading.Lock()


def config_for(cid: str) -> RuntimeConfig:
    with _lock:
        return _CONFIGS.setdefault(cid, RuntimeConfig())


def effective_key_set(provider: str | None, cfg: RuntimeConfig) -> bool:
    """True if an API key is available for the resolved provider (this client)."""
    if cfg.api_key:
        return True
    resolved = (provider or os.environ.get("LLM_PROVIDER") or "anthropic").lower()
    if resolved == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if resolved in ("openai", "openai-compatible"):
        return bool(os.environ.get("OPENAI_API_KEY"))
    return False


def any_override(cfg: RuntimeConfig) -> bool:
    return any([cfg.provider, cfg.model, cfg.base_url, cfg.api_key])
