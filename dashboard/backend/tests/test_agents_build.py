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


# ---------------------------------------------------------------------------
# Task 6 (KB-T6): propose_scaffold threads knowledge_bases into manifest
# ---------------------------------------------------------------------------

def test_scaffold_with_knowledge_bases_produces_kb_entry():
    """propose_scaffold with knowledge_bases produces a BizKnowledgeInfo entry."""
    import json
    params = {
        "name": "KB Test", "language": "ENG", "branch": "dev",
        "custom_intents": [
            {"name": "FAQ_Intent", "language": "ENG",
             "keywords": ["help"], "user_responses": ["I need help"]}
        ],
        "canvases": [
            {"name": "Main", "nodes": [{"id": "greet", "prompt": "Hello, how can I help?"}]},
        ],
        "knowledge_bases": [
            {"name": "FAQ KB", "intents": ["FAQ_Intent"], "answers": ["We are happy to help."]}
        ],
    }
    r = agents.propose_scaffold(params)
    assert r["ok"], r.get("error")
    proposed = r["proposed_data"]
    # BizKnowledgeInfo may be a JSON string or list
    raw = proposed.get("BizKnowledgeInfo", "[]")
    kb_list = json.loads(raw) if isinstance(raw, str) else raw
    assert len(kb_list) >= 1, "Expected at least one BizKnowledgeInfo entry"
    titles = [kb.get("kdTitle") for kb in kb_list]
    assert "FAQ KB" in titles, f"KB 'FAQ KB' not found; got: {titles}"


def test_scaffold_knowledge_bases_name_distinct_when_declared():
    """propose_scaffold with knowledge_bases produces a KB with the declared name,
    distinct from any default KBs the builder always emits."""
    import json
    params_with_kb = {
        "name": "KB Name Test", "language": "ENG", "branch": "dev",
        "custom_intents": [
            {"name": "My_Intent", "language": "ENG",
             "keywords": ["query"], "user_responses": ["My query"]}
        ],
        "canvases": [
            {"name": "Main", "nodes": [{"id": "greet", "prompt": "Hi"}]},
        ],
        "knowledge_bases": [
            {"name": "My Declared KB", "intents": ["My_Intent"],
             "answers": ["Here is the answer."]}
        ],
    }
    r = agents.propose_scaffold(params_with_kb)
    assert r["ok"], r.get("error")
    raw = r["proposed_data"].get("BizKnowledgeInfo", "[]")
    kb_list = json.loads(raw) if isinstance(raw, str) else raw
    titles = [kb.get("kdTitle") for kb in kb_list]
    assert "My Declared KB" in titles, f"Declared KB not found; got: {titles}"
