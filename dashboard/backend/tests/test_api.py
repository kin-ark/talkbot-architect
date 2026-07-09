"""Tests for model catalog integration in config resolution."""
from __future__ import annotations


def test_models_endpoint_lists_catalog_no_secrets():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.get("/models")
    assert r.status_code == 200
    body = r.json()
    ids = {m["id"] for m in body["models"]}
    assert {"claude-opus-4-8", "deepseek-chat"} <= ids
    assert body["default"] in ids
    for m in body["models"]:
        assert set(m) == {"id", "label", "provider", "base_url", "group"}
        assert "api_key" not in m and "model" not in m   # no secret / exact-model leak


def test_config_model_id_resolves_deepseek(monkeypatch):
    # picking deepseek-chat must build a client with the DeepSeek model+base_url,
    # NEVER the LLM_MODEL env default (the original bug).
    monkeypatch.setenv("LLM_MODEL", "claude-opus-4-8")  # the leaky env
    import config_store
    import main
    captured = {}

    class _FakeClient:
        def __init__(self, **kw):
            captured.update(kw)
            self.model = kw["model"]

    def _fake_make_client(*, provider, api_key, model, base_url, thinking_budget=None):
        return _FakeClient(provider=provider, api_key=api_key or "k",
                           model=model, base_url=base_url)

    monkeypatch.setattr(main, "make_client", _fake_make_client)
    cid = "test-cid-ds"
    cfg = config_store.config_for(cid)
    cfg.model_id = "deepseek-chat"
    cfg.api_key = "sk-test"
    client = main.get_client(cid)
    assert client.model == "deepseek-chat"
    assert captured["base_url"] == "https://api.deepseek.com/anthropic"
    assert captured["model"] != "claude-opus-4-8"


def test_config_unset_model_id_uses_catalog_default_not_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "some-leaky-model")
    import config_store
    import main
    import models_catalog
    captured = {}

    class _FakeClient:
        def __init__(self, **kw):
            captured.update(kw)
            self.model = kw["model"]

    monkeypatch.setattr(main, "make_client",
                        lambda **kw: _FakeClient(**{**kw, "api_key": "k"}))
    cid = "test-cid-default"
    config_store.config_for(cid).api_key = "sk-test"
    main.get_client(cid)
    assert captured["model"] == models_catalog.entry_by_id(
        models_catalog.default_entry_id()).model
    assert captured["model"] != "some-leaky-model"


def test_put_config_sets_model_id_and_returns_derived():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.put("/config", json={"model_id": "deepseek-chat"})
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "deepseek-chat"
    assert body["base_url"] == "https://api.deepseek.com/anthropic"
    assert body["provider"] == "anthropic"
    assert "model_id" in body and body["model_id"] == "deepseek-chat"
