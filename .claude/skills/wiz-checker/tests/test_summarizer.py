import json
import pytest
from wizcheck.parser import parse_dict
from wizcheck.summarizer import build_summary_tree


def test_empty_returns_empty_shape():
    """parse_dict with no components/KBs -> {"mainFlow": [], "knowledgeBases": []}."""
    wf = parse_dict({"BizSpeechComponent": [], "SpeechVariable": "[]", "SpeechIntent": "[]"})
    out = build_summary_tree(wf)
    assert out == {"mainFlow": [], "knowledgeBases": []}


def _make_export_with_two_nodes() -> dict:
    """Minimal export: one component, entry node -> child node (Unclassified intent)."""
    entry_uuid = "aaaaaaaa-0000-0000-0000-000000000001"
    child_uuid = "bbbbbbbb-0000-0000-0000-000000000002"
    intent_port = "cccccccc-0000-0000-0000-000000000003"

    details = {
        entry_uuid: {
            "name": "Entry Node",
            "type": 1,
            "is_default": True,
            "data": {
                "type": 1,
                "list": [{"text": "Hello"}],
                "all_client_intent": [{"id": intent_port, "name": "Unclassified"}],
                "node_variables": [],
                "allow_jump_knowledges": [],
            },
        },
        child_uuid: {
            "name": "Child Node",
            "type": 1,
            "is_default": False,
            "data": {
                "type": 1,
                "list": [{"text": "Goodbye"}],
                "all_client_intent": [],
                "node_variables": [],
                "allow_jump_knowledges": [],
            },
        },
    }
    routes = {
        entry_uuid: {
            intent_port: {"target": {"uuid": child_uuid}},
        }
    }
    comp = {
        "componentUuid": "dddddddd-0000-0000-0000-000000000004",
        "name": "Main Component",
        "sortIndex": 0,
        "details": json.dumps(details),
        "routes": json.dumps(routes),
    }
    return {
        "BizSpeechComponent": [comp],
        "SpeechVariable": "[]",
        "SpeechIntent": "[]",
    }


def test_tree_built_from_flow_model():
    """2-node component (entry -> child via Unclassified): tree has entry at root with child."""
    data = _make_export_with_two_nodes()
    wf = parse_dict(data)
    out = build_summary_tree(wf)

    assert "mainFlow" in out
    assert len(out["mainFlow"]) == 1

    comp_tree = out["mainFlow"][0]
    # Component tree should have children (the entry node)
    assert comp_tree["children"], "expected entry node at top of component tree"

    entry_node = comp_tree["children"][0]
    # The entry node must have a child (the child node)
    assert entry_node.get("children"), "entry node should have a child"
    assert entry_node["children"][0]["name"]  # child should have a name
