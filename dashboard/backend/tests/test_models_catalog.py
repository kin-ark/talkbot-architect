import json

import pytest


def test_builtin_catalog_is_claude_defaults_only():
    import models_catalog as mc
    ids = {e.id for e in mc.load_catalog()}
    assert {"claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5"} <= ids
    assert "deepseek-chat" not in ids and "deepseek-reasoner" not in ids  # now via Custom
    for e in mc.load_catalog():
        assert e.provider == "anthropic" and e.base_url is None


def test_custom_sentinel_and_providers_exported():
    import models_catalog as mc
    assert mc.CUSTOM_MODEL_ID == "__custom__"
    assert mc.entry_by_id(mc.CUSTOM_MODEL_ID) is None       # sentinel is NOT a catalog entry
    assert mc.PROVIDERS == ["anthropic", "openai", "openai-compatible"]


def test_default_entry_id_is_a_real_entry():
    import models_catalog as mc
    assert mc.entry_by_id(mc.default_entry_id()) is not None


def test_env_json_appends_and_overrides(monkeypatch):
    import models_catalog as mc
    override = [
        {"id": "my-model", "label": "My Model", "provider": "anthropic",
         "model": "custom-1", "base_url": "https://x.example/anthropic", "group": "Custom"},
        {"id": "claude-opus-4-8", "label": "Opus (renamed)", "provider": "anthropic",
         "model": "claude-opus-4-8", "base_url": None, "group": "Claude"},
    ]
    monkeypatch.setenv("LLM_MODELS_JSON", json.dumps(override))
    entries = mc.load_catalog()
    assert mc.entry_by_id("my-model") is not None       # appended
    assert mc.entry_by_id("claude-opus-4-8").label == "Opus (renamed)"  # overridden by id


def test_malformed_env_json_falls_back_to_builtin(monkeypatch):
    import models_catalog as mc
    monkeypatch.setenv("LLM_MODELS_JSON", "{not json")
    entries = mc.load_catalog()          # must not raise
    assert mc.entry_by_id("claude-opus-4-8") is not None


def test_default_model_id_env_override(monkeypatch):
    import models_catalog as mc
    monkeypatch.setenv("LLM_DEFAULT_MODEL_ID", "claude-sonnet-5")
    assert mc.default_entry_id() == "claude-sonnet-5"
    monkeypatch.setenv("LLM_DEFAULT_MODEL_ID", "does-not-exist")
    assert mc.entry_by_id(mc.default_entry_id()) is not None   # bad value ignored
