"""Tests for GET /config and PUT /config endpoints (Task FA1)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import config_store
import main
from main import app

http = TestClient(app)


# ---------------------------------------------------------------------------
# autouse fixture: reset CONFIG between every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_config():
    """Reset the in-memory RuntimeConfig before each test."""
    config_store.CONFIG.provider = None
    config_store.CONFIG.model = None
    config_store.CONFIG.base_url = None
    config_store.CONFIG.api_key = None
    yield
    config_store.CONFIG.provider = None
    config_store.CONFIG.model = None
    config_store.CONFIG.base_url = None
    config_store.CONFIG.api_key = None


# ---------------------------------------------------------------------------
# GET /config — before any override
# ---------------------------------------------------------------------------

def test_get_config_source_env_when_no_override(monkeypatch):
    """With no override, source should be 'env'."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = http.get("/config")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "env"
    assert body["key_set"] is False


def test_get_config_key_set_true_when_env_key_present(monkeypatch):
    """key_set should be True when ANTHROPIC_API_KEY is in env and provider resolves to anthropic."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    r = http.get("/config")
    assert r.status_code == 200
    body = r.json()
    assert body["key_set"] is True
    # The key value must NEVER appear in the response
    assert "sk-env-key" not in r.text


def test_get_config_key_value_never_in_response(monkeypatch):
    """API key value must never appear anywhere in the /config response."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "super-secret-value-abc123")
    r = http.get("/config")
    assert "super-secret-value-abc123" not in r.text


# ---------------------------------------------------------------------------
# PUT /config
# ---------------------------------------------------------------------------

def test_put_config_sets_fields_and_returns_correct_shape():
    """PUT /config updates provider/model/base_url and returns GET-shaped response."""
    payload = {
        "provider": "openai",
        "model": "gpt-4o",
        "base_url": "http://lite",
        "api_key": "sk-x",
    }
    r = http.put("/config", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-4o"
    assert body["base_url"] == "http://lite"
    assert body["key_set"] is True
    assert body["source"] == "override"
    # The key value must NEVER appear in the response
    assert "sk-x" not in r.text
    # Confirm the "api_key" field itself is absent (not just masked)
    assert "api_key" not in body


def test_put_config_source_becomes_override():
    """After any PUT, source should be 'override'."""
    r = http.put("/config", json={"provider": "anthropic"})
    assert r.json()["source"] == "override"


def test_put_config_empty_api_key_does_not_clear_existing():
    """An empty-string api_key in PUT should not overwrite an existing key."""
    config_store.CONFIG.api_key = "already-set"
    r = http.put("/config", json={"api_key": ""})
    assert r.status_code == 200
    # existing key should still be in CONFIG
    assert config_store.CONFIG.api_key == "already-set"


def test_put_config_key_value_never_in_response():
    """api_key value must never appear in PUT /config response."""
    r = http.put("/config", json={"api_key": "do-not-leak-me-xyz"})
    assert "do-not-leak-me-xyz" not in r.text


# ---------------------------------------------------------------------------
# GET /config after PUT — roundtrip
# ---------------------------------------------------------------------------

def test_get_config_after_put_shows_override(monkeypatch):
    """GET /config after a PUT should reflect the overridden values."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    http.put("/config", json={
        "provider": "openai",
        "model": "gpt-4o",
        "base_url": "http://lite",
        "api_key": "sk-x",
    })
    r = http.get("/config")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-4o"
    assert body["base_url"] == "http://lite"
    assert body["key_set"] is True
    assert body["source"] == "override"
    assert "sk-x" not in r.text


# ---------------------------------------------------------------------------
# /config/clear (nice-to-have)
# ---------------------------------------------------------------------------

def test_config_clear_resets_to_env(monkeypatch):
    """POST /config/clear should reset CONFIG and return source='env'."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config_store.CONFIG.provider = "openai"
    config_store.CONFIG.api_key = "sk-x"
    r = http.post("/config/clear")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "env"
    assert config_store.CONFIG.provider is None
    assert config_store.CONFIG.api_key is None


# ---------------------------------------------------------------------------
# get_client uses override (integration-style, monkeypatch make_client)
# ---------------------------------------------------------------------------

def test_get_client_uses_config_override(monkeypatch):
    """get_client() should build client from CONFIG override when set."""
    captured = {}

    def fake_make_client(provider, api_key, model, base_url=None):
        captured["provider"] = provider
        captured["api_key"] = api_key
        captured["model"] = model
        captured["base_url"] = base_url
        from llm.base import FakeLLMClient
        return FakeLLMClient(script=[])

    monkeypatch.setattr("main.make_client", fake_make_client)

    config_store.CONFIG.provider = "openai"
    config_store.CONFIG.model = "gpt-4o"
    config_store.CONFIG.base_url = "http://lite"
    config_store.CONFIG.api_key = "sk-override"

    client = main.get_client()  # type: ignore[call-arg]

    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-4o"
    assert captured["base_url"] == "http://lite"
    assert captured["api_key"] == "sk-override"
    _ = client  # used
