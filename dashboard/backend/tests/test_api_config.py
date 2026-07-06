"""Tests for GET /config and PUT /config endpoints (per-client model)."""
from __future__ import annotations

from fastapi.testclient import TestClient

import main
from main import app

http = TestClient(app)


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
    # Pre-set the key via a proper PUT
    http.put("/config", json={"api_key": "already-set"})
    r = http.put("/config", json={"api_key": ""})
    assert r.status_code == 200
    # The config should still report key_set=True (key still present)
    assert r.json()["key_set"] is True


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
    """POST /config/clear should reset config and return source='env'."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # First set some overrides
    http.put("/config", json={"provider": "openai", "api_key": "sk-x"})
    r = http.post("/config/clear")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "env"
    # Verify the GET also reflects cleared state
    r2 = http.get("/config")
    assert r2.json()["source"] == "env"


# ---------------------------------------------------------------------------
# get_client uses override (integration-style, monkeypatch make_client)
# ---------------------------------------------------------------------------

def test_get_client_uses_config_override(monkeypatch):
    """get_client() should build client from config override when set."""
    captured = {}

    def fake_make_client(provider, api_key, model, base_url=None, thinking_budget=None):
        captured["provider"] = provider
        captured["api_key"] = api_key
        captured["model"] = model
        captured["base_url"] = base_url
        captured["thinking_budget"] = thinking_budget
        from llm.base import FakeLLMClient
        return FakeLLMClient(script=[])

    monkeypatch.setattr("main.make_client", fake_make_client)

    # Set config via API (using the shared http client's tbid)
    http.put("/config", json={
        "provider": "openai",
        "model": "gpt-4o",
        "base_url": "http://lite",
        "api_key": "sk-override",
    })

    # Get the cid from the shared client's cookie
    tbid = http.cookies.get("tbid", "_legacy")

    # Directly invoke get_client with the cid (bypassing FastAPI dependency injection)
    client_obj = main.get_client(cid=tbid)

    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-4o"
    assert captured["base_url"] == "http://lite"
    assert captured["api_key"] == "sk-override"
    _ = client_obj  # used
