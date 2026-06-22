"""Tests for agents.propose_build (Task 13).

Step 1: failing test (RED).
Step 4: should pass after implementation (GREEN).
"""
from pathlib import Path
import agents

_MANIFEST = (Path(__file__).resolve().parents[3]
             / ".claude/skills/wiz-builder/tests/fixtures/manifest_minimal.yaml")


def test_propose_build_produces_checker_clean_data():
    res = agents.propose_build(_MANIFEST.read_text(encoding="utf-8"))
    assert res["ok"] is True
    assert isinstance(res["proposed_data"], dict)
    errors = [f for f in agents.validate(res["proposed_data"]) if f["severity"] == "error"]
    assert errors == []
