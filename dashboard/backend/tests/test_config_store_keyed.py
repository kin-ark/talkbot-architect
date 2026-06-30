import config_store


def test_config_for_isolates_clients():
    config_store._CONFIGS.clear()
    a = config_store.config_for("alice")
    b = config_store.config_for("bob")
    a.provider = "anthropic"
    a.api_key = "sk-a"
    assert b.provider is None and b.api_key is None
    # same id returns the same object
    assert config_store.config_for("alice") is a


def test_effective_key_set_uses_passed_cfg(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = config_store.RuntimeConfig()
    assert config_store.effective_key_set("anthropic", cfg) is False
    cfg.api_key = "sk-x"
    assert config_store.effective_key_set("anthropic", cfg) is True


def test_any_override(monkeypatch):
    cfg = config_store.RuntimeConfig()
    assert config_store.any_override(cfg) is False
    cfg.model = "claude-opus-4-8"
    assert config_store.any_override(cfg) is True
