"""Tests for get_playbook tool (Task 2).

Step 1: failing tests (RED).
Step 4: should pass after implementation (GREEN).
"""
from __future__ import annotations

import agents
from tools import registry


def test_agents_get_playbook_found():
    r = agents.get_playbook("debt_collection")
    assert r["found"] is True and r["vertical"] == "debt_collection"
    assert r["playbook"] and "Convincer" in r["playbook"]


def test_agents_get_playbook_not_found_lists_available():
    r = agents.get_playbook("nope")
    assert r["found"] is False and r["playbook"] is None
    assert "debt_collection" in r["available"]


def test_get_playbook_tool_registered_and_dispatches():
    names = {t.name for t in registry.tool_specs()}
    assert "get_playbook" in names
    out = registry.dispatch("get_playbook", {"vertical": "debt_collection"}, {})
    assert out["proposal"] is None
    assert out["result"]["found"] is True
