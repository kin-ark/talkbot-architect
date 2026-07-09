import json

import pytest


def test_builtin_catalog_has_starter_entries():
    import models_catalog as mc
    entries = mc.load_catalog()
    ids = {e.id for e in entries}
    assert {"claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5",
            "deepseek-chat", "deepseek-reasoner"} <= ids
    ds = mc.entry_by_id("deepseek-chat")
    assert ds.provider == "anthropic"
    assert ds.model == "deepseek-chat"
    assert ds.base_url == "https://api.deepseek.com/anthropic"
    assert ds.group == "DeepSeek"
    opus = mc.entry_by_id("claude-opus-4-8")
    assert opus.base_url is None and opus.model == "claude-opus-4-8"


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
    monkeypatch.setenv("LLM_DEFAULT_MODEL_ID", "deepseek-chat")
    assert mc.default_entry_id() == "deepseek-chat"
    monkeypatch.setenv("LLM_DEFAULT_MODEL_ID", "does-not-exist")
    assert mc.entry_by_id(mc.default_entry_id()) is not None   # bad value ignored
