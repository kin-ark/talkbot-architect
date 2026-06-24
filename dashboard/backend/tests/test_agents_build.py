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


def test_scaffold_with_goto_and_exit_nodes():
    params = {
        "name": "Gap Test", "language": "IDN", "branch": "dev",
        "canvases": [
            {"name": "1. Greeting", "nodes": [
                {"id": "open", "prompt": "Halo"},
                {"id": "jump", "prompt": "(goto)", "type": "goto", "config": {"target": "2. Next"}},
            ], "edges": [{"from": "open", "branch": "Unclassified", "to": "jump"}]},
            {"name": "2. Next", "nodes": [
                {"id": "open2", "prompt": "Lanjut"},
                {"id": "bye", "prompt": "Terima kasih", "type": "exit"},
            ], "edges": [{"from": "open2", "branch": "Unclassified", "to": "bye"}]},
        ],
    }
    r = agents.propose_scaffold(params)
    assert r["ok"], r.get("error")
    import json
    comps = json.loads(r["proposed_data"]["BizSpeechComponent"])
    types = sorted(n.get("type") for c in comps for n in json.loads(c["details"]).values())
    assert 4 in types and 2 in types  # goto(4) + exit(2) present
