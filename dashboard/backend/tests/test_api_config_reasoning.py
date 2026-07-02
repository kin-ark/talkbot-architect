"""Tests for show_reasoning config field."""
from __future__ import annotations

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_config_includes_show_reasoning_default_true():
    r = client.get("/config")
    assert r.status_code == 200
    assert r.json()["show_reasoning"] is True


def test_put_config_sets_show_reasoning():
    client.put("/config", json={"show_reasoning": False})
    assert client.get("/config").json()["show_reasoning"] is False
    client.put("/config", json={"show_reasoning": True})
    assert client.get("/config").json()["show_reasoning"] is True


def test_clear_config_resets_show_reasoning_true():
    client.put("/config", json={"show_reasoning": False})
    client.post("/config/clear")
    assert client.get("/config").json()["show_reasoning"] is True
