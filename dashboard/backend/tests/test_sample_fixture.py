"""Tests guarding the sample_export fixture stays valid.

Uses the synthetic fixture at tests/fixtures/sample_export.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure dashboard/backend is importable (mirrors conftest.py pattern)
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import agents  # noqa: E402 (after sys.path setup)
from tests.fixtures import load_sample, KNOWN_NODE_UUID  # noqa: E402


def test_fixture_builds_valid():
    """The fixture must have 0 errors and ≥3 components."""
    data = load_sample()
    errs = [f for f in agents.validate(data) if f["severity"] == "error"]
    assert errs == [], f"Expected 0 errors, got: {errs}"

    s = agents.summarize(data)
    assert len(s["components"]) >= 3, f"Expected ≥3 components, got {len(s['components'])}"


def test_fixture_has_findings_and_known_node():
    """The fixture must have ≥1 warning and the known node must be resolvable."""
    data = load_sample()
    findings = agents.validate(data)
    assert any(
        f["severity"] == "warning" for f in findings
    ), "Expected ≥1 warning in fixture"

    result = agents.read_node(data, KNOWN_NODE_UUID)
    assert result is not None, f"Known node {KNOWN_NODE_UUID} not found in fixture"
