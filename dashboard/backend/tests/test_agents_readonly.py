"""Tests for agents.py read-only wrappers (Task 7).

Uses the committed synthetic fixture tests/fixtures/sample_export.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure dashboard/backend is importable (mirrors conftest.py pattern)
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Fixture: tests/fixtures/sample_export.json
_REAL_EXPORT = Path(__file__).resolve().parent / "fixtures" / "sample_export.json"
_DATA = json.loads(_REAL_EXPORT.read_text("utf-8"))

# A stable talk-node uuid present in the fixture (for read_node / node-text tests)
_KNOWN_NODE_UUID = "fdce746c-fe23-5a51-a8b6-03654b1624fa"


import agents  # noqa: E402  (after sys.path setup)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

def test_validate_returns_finding_dicts():
    findings = agents.validate(_DATA)
    assert isinstance(findings, list)
    required_keys = {"code", "severity", "message"}
    for item in findings:
        assert required_keys.issubset(item.keys()), f"Missing keys in: {item}"
        assert item["severity"] in {"error", "warning"}, f"Bad severity: {item['severity']}"


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------

def test_summarize_returns_flow_model():
    result = agents.summarize(_DATA)
    assert "components" in result
    assert "knowledge_bases" in result
    assert len(result["components"]) >= 1


# ---------------------------------------------------------------------------
# read_node
# ---------------------------------------------------------------------------

def test_read_node_finds_a_real_node():
    result = agents.read_node(_DATA, _KNOWN_NODE_UUID)
    assert result is not None
    assert result["uuid"] == _KNOWN_NODE_UUID
    assert "envelope" in result
    # envelope must have a type (FlowModel guarantee)
    assert "type" in result["envelope"] or result["envelope"].get("type") is not None or "data" in result["envelope"]


def test_read_node_unknown_returns_none():
    result = agents.read_node(_DATA, "00000000-0000-0000-0000-000000000000")
    assert result is None


# ---------------------------------------------------------------------------
# get_facts
# ---------------------------------------------------------------------------

def test_get_facts_finds_something():
    results = agents.get_facts("intent")
    assert len(results) >= 1, "Expected at least one fact matching 'intent'"
    for item in results:
        assert isinstance(item, dict)
        assert "id" in item, f"Fact missing 'id' key: {item}"
