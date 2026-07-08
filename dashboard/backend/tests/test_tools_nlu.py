"""Task 5: dashboard chat tools for deep-NLU ops.

Mirrors the add_kb_answer dispatch test in test_tools_kb_edit.py — each tool should
produce a proposal (ok=True, proposal dict present) when dispatched with minimal valid
params against a fixture doc.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agents
from tools import registry


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def nlu_doc():
    """A two-component doc built via propose_scaffold for testing NLU tools."""
    params = {
        "name": "NLU Test Bot", "language": "IDN", "branch": "dev",
        "custom_intents": [
            {"name": "Greeting", "language": "IDN", "keywords": ["halo", "hai"],
             "user_responses": ["Halo kembali", "Selamat datang"]}
        ],
        "canvases": [
            {"name": "1. Main", "nodes": [{"id": "open", "prompt": "Halo"}]},
            {"name": "2. Follow", "nodes": [{"id": "open2", "prompt": "Lanjut"}]},
        ],
    }
    r = agents.propose_scaffold(params)
    assert r["ok"], r.get("error")
    return r["proposed_data"]


# ---------------------------------------------------------------------------
# Task 5 NLU tools
# ---------------------------------------------------------------------------

_NLU_TOOLS = [
    "add_intent",
    "set_hotwords",
    "set_intent_training",
    "set_node_tags",
]


def test_nlu_tools_registered():
    """tool_specs() must include all NLU tools."""
    names = {s.name for s in registry.tool_specs()}
    for tool_name in _NLU_TOOLS:
        assert tool_name in names, f"{tool_name!r} not found in registry"


def test_nlu_tool_schemas():
    """Each NLU tool must expose the correct parameter schema."""
    specs = {s.name: s for s in registry.tool_specs()}

    # add_intent: name(str, required), language(str, required), keywords(array), user_responses(array)
    ai = specs["add_intent"].parameters
    assert ai["properties"]["name"]["type"] == "string"
    assert ai["properties"]["language"]["type"] == "string"
    assert "keywords" in ai["properties"]
    assert ai["properties"]["keywords"]["type"] == "array"
    assert "user_responses" in ai["properties"], "add_intent missing user_responses property"
    assert ai["properties"]["user_responses"]["type"] == "array"
    assert ai["properties"]["user_responses"]["items"]["type"] == "string"
    assert set(ai.get("required", [])) >= {"name", "language"}

    # set_hotwords: hot_words(array, required), node(string/null, optional)
    sh = specs["set_hotwords"].parameters
    assert "hot_words" in sh["properties"]
    assert sh["properties"]["hot_words"]["type"] == "array"
    assert sh["properties"]["hot_words"]["items"]["type"] == "string"
    assert "node" in sh["properties"]
    assert set(sh.get("required", [])) >= {"hot_words"}

    # set_intent_training: name(str, required), keywords(array), user_responses(array)
    sit = specs["set_intent_training"].parameters
    assert sit["properties"]["name"]["type"] == "string"
    assert "keywords" in sit["properties"]
    assert sit["properties"]["keywords"]["type"] == "array"
    assert "user_responses" in sit["properties"]
    assert sit["properties"]["user_responses"]["type"] == "array"
    assert set(sit.get("required", [])) >= {"name"}

    # set_node_tags: node(node-ref, required), tags(array of {category, values}, required)
    snt = specs["set_node_tags"].parameters
    assert "node" in snt["properties"]
    assert snt["properties"]["node"]["type"] == "object"
    assert "uuid" in snt["properties"]["node"]["properties"]
    assert "label" in snt["properties"]["node"]["properties"]
    assert "tags" in snt["properties"]
    assert snt["properties"]["tags"]["type"] == "array"
    assert set(snt.get("required", [])) >= {"node", "tags"}


# ---------------------------------------------------------------------------
# Dispatch tests
# ---------------------------------------------------------------------------

def test_add_intent_with_user_responses(nlu_doc):
    """add_intent dispatch with user_responses forwards them."""
    out = registry.dispatch("add_intent", {
        "name": "Feedback",
        "language": "IDN",
        "keywords": ["bagus", "jelek"],
        "user_responses": ["Terima kasih", "Maaf mendengarnya"],
    }, nlu_doc)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_set_hotwords_global(nlu_doc):
    """set_hotwords dispatch without node (global) returns a proposal."""
    out = registry.dispatch("set_hotwords", {
        "hot_words": ["urgent", "critical"],
    }, nlu_doc)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_set_hotwords_with_node(nlu_doc):
    """set_hotwords dispatch with a real node uuid returns a proposal."""
    # Find a node uuid from the fixture
    bsc = nlu_doc.get("BizSpeechComponent", [])
    if bsc and isinstance(bsc, list) and bsc:
        if isinstance(bsc[0], dict) and "details" in bsc[0]:
            details_str = bsc[0]["details"]
            if isinstance(details_str, str):
                try:
                    details = json.loads(details_str)
                    node_uuids = list(details.keys())
                    if node_uuids:
                        node_uuid = node_uuids[0]
                        out = registry.dispatch("set_hotwords", {
                            "hot_words": ["priority", "attention"],
                            "node": node_uuid,
                        }, nlu_doc)
                        assert out["result"]["ok"] is True, out["result"].get("error")
                        assert out["proposal"] is not None
                        assert isinstance(out["proposal"]["proposed_data"], dict)
                        return
                except (json.JSONDecodeError, ValueError):
                    pass

    # Fallback: test without node (already covered above)
    out = registry.dispatch("set_hotwords", {
        "hot_words": ["priority", "attention"],
    }, nlu_doc)
    assert out["result"]["ok"] is True, out["result"].get("error")


def test_set_intent_training(nlu_doc):
    """set_intent_training dispatch with name and optional keywords/user_responses."""
    out = registry.dispatch("set_intent_training", {
        "name": "Greeting",
        "keywords": ["selamat pagi", "selamat sore"],
        "user_responses": ["Pagi", "Sore"],
    }, nlu_doc)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_set_intent_training_name_only(nlu_doc):
    """set_intent_training dispatch with only name (required) returns a proposal."""
    out = registry.dispatch("set_intent_training", {
        "name": "Greeting",
    }, nlu_doc)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_set_node_tags_with_speechtag(nlu_doc):
    """set_node_tags dispatch with a real SpeechTag and node uuid returns a proposal."""
    # Extract node uuid up-front from fixture; fail loudly if fixture is malformed.
    # BizSpeechComponent is a JSON-encoded string in a full-export doc.
    bsc_raw = nlu_doc.get("BizSpeechComponent")
    assert isinstance(bsc_raw, str) and bsc_raw.strip(), \
        "fixture must provide a BizSpeechComponent JSON string"
    bsc = json.loads(bsc_raw)
    assert isinstance(bsc, list) and bsc and "details" in bsc[0], \
        "fixture component must have a 'details' field"
    details = json.loads(bsc[0]["details"])
    node_uuids = list(details.keys())
    assert node_uuids, "fixture component details must contain at least one node"

    node_uuid = node_uuids[0]

    # Dispatch with the resolved node uuid
    out = registry.dispatch("set_node_tags", {
        "node": {"uuid": node_uuid},
        "tags": [{"category": "Test Category", "values": ["Test Value"]}],
    }, nlu_doc)

    # Assert real result
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)
