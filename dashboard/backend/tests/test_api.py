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
    assert {"claude-opus-4-8"} <= ids
    assert body["default"] in ids
    for m in body["models"]:
        assert set(m) == {"id", "label", "provider", "base_url", "group"}
        assert "api_key" not in m and "model" not in m   # no secret / exact-model leak


def test_config_model_id_resolves_deepseek(monkeypatch):
    # The DeepSeek built-in catalog entry was removed; now it routes via custom model.
    # Test that setting model_id="__custom__" with typed provider/model/base_url works.
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
    cfg.model_id = "__custom__"
    cfg.provider = "anthropic"
    cfg.model = "deepseek-chat"
    cfg.base_url = "https://api.deepseek.com/anthropic"
    cfg.api_key = "sk-test"
    client = main.get_client(cid)
    assert client.model == "deepseek-chat"
    assert captured["base_url"] == "https://api.deepseek.com/anthropic"
    assert captured["provider"] == "anthropic"
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
    r = c.put("/config", json={"model_id": "claude-opus-4-8"})
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "claude-opus-4-8"
    assert body["provider"] == "anthropic"
    assert "model_id" in body and body["model_id"] == "claude-opus-4-8"


def test_chat_audit_log_uses_resolved_model_not_env(monkeypatch):
    # Regression: /chat logged `cfg.model or LLM_MODEL`, so the new UI (sends
    # only model_id -> cfg.model is None) mislabeled every turn as the env
    # default (opus). The log must record the catalog-resolved model.
    import logging

    import config_store
    import main

    monkeypatch.setenv("LLM_MODEL", "claude-opus-4-8")  # the leaky env default

    class _FakeClient:
        def __init__(self):
            self.model = "claude-sonnet-5"

    class _FakeSession:
        _stack = [object()]

        class _Lock:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        _lock = _Lock()

        def _autosave(self):
            pass

    cid = "test-cid-chatlog"
    cfg = config_store.config_for(cid)
    cfg.model_id = "claude-sonnet-5"

    main.app.dependency_overrides[main.get_client] = lambda: _FakeClient()
    main.app.dependency_overrides[main.current_session] = lambda: _FakeSession()
    main.app.dependency_overrides[main.client_id] = lambda: cid
    monkeypatch.setattr(main, "run_turn", lambda client, s, msg: {"ok": True})

    # The app logger ("tba") has propagate=False + a JSON stdout handler, so
    # neither caplog nor capsys see it; attach a list handler directly.
    records = []

    class _ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _ListHandler()
    main.log.addHandler(handler)
    try:
        from fastapi.testclient import TestClient
        c = TestClient(main.app)
        r = c.post("/chat", json={"message": "hi"})
        assert r.status_code == 200
        llm_recs = [r for r in records if getattr(r, "ev", None) == "llm"]
        assert llm_recs, "no llm audit log record emitted"
        assert llm_recs[-1].model == "claude-sonnet-5"
        assert llm_recs[-1].model != "claude-opus-4-8"
    finally:
        main.log.removeHandler(handler)
        main.app.dependency_overrides.clear()


def test_models_endpoint_exposes_custom_and_providers():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    body = c.get("/models").json()
    assert body["custom_id"] == "__custom__"
    assert body["providers"] == ["anthropic", "openai", "openai-compatible"]
    for m in body["models"]:
        assert set(m) == {"id", "label", "provider", "base_url", "group"}
        assert "api_key" not in m


def test_resolve_custom_model_uses_typed_values(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "claude-opus-4-8")  # must NOT leak
    import config_store
    import main
    captured = {}

    class _Fake:
        def __init__(self, **kw):
            captured.update(kw)
            self.model = kw["model"]

    monkeypatch.setattr(main, "make_client",
                        lambda **kw: _Fake(**{**kw, "api_key": kw.get("api_key") or "k"}))
    cid = "cid-custom"
    cfg = config_store.config_for(cid)
    cfg.model_id = "__custom__"
    cfg.provider = "openai-compatible"
    cfg.model = "deepseek-chat"
    cfg.base_url = "https://api.deepseek.com/anthropic"
    cfg.api_key = "sk-x"
    client = main.get_client(cid)
    assert client.model == "deepseek-chat"
    assert captured["provider"] == "openai-compatible"
    assert captured["base_url"] == "https://api.deepseek.com/anthropic"
    assert captured["model"] != "claude-opus-4-8"


def test_resolve_claude_default_user_base_url_wins(monkeypatch):
    import config_store
    import main
    captured = {}

    class _Fake:
        def __init__(self, **kw):
            captured.update(kw)
            self.model = kw["model"]

    monkeypatch.setattr(main, "make_client",
                        lambda **kw: _Fake(**{**kw, "api_key": kw.get("api_key") or "k"}))
    cid = "cid-proxy"
    cfg = config_store.config_for(cid)
    cfg.model_id = "claude-opus-4-8"
    cfg.base_url = "https://my-proxy.example/anthropic"   # user proxy overrides entry None
    cfg.api_key = "sk-x"
    main.get_client(cid)
    assert captured["model"] == "claude-opus-4-8"
    assert captured["base_url"] == "https://my-proxy.example/anthropic"


def test_resolve_custom_blank_model_raises(monkeypatch):
    import config_store
    import main
    from llm.factory import LLMConfigError
    from fastapi import HTTPException
    import pytest
    cid = "cid-blank"
    cfg = config_store.config_for(cid)
    cfg.model_id = "__custom__"
    cfg.provider = "anthropic"
    cfg.model = ""                 # nothing typed
    cfg.api_key = "sk-x"
    with pytest.raises((LLMConfigError, HTTPException)):
        main.get_client(cid)
