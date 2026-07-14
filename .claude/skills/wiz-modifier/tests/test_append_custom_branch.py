import json
from pathlib import Path

import pytest
from wizmodifier.apply import run_mods
from wizmodifier.io import InputBundle

BASELINE = Path(__file__).parent / "fixtures" / "Empty+Dialogue.zip"


def _load():
    return InputBundle.load(BASELINE)


def _comp0_details(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    d = comps[0].get("details")
    return json.loads(d) if isinstance(d, str) and d not in ("null", "") else {}


def _bundle_with_intent_and_node():
    """Load the baseline, add a custom intent "PaidCash", and append node "n1"
    (an existing node the new node's edges can target)."""
    b = _load()
    run_mods(b, [{"op": "add-intent", "name": "PaidCash"}], manifest_hash="t")
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "n1", "prompt": "First"}}], manifest_hash="t")
    return b


def test_append_talk_with_custom_branch():
    b = _bundle_with_intent_and_node()
    n1_uuid = next(iter(_comp0_details(b).keys()))
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "ask2", "prompt": "Paid?",
                           "config": {"branch_intents": {"Paid": ["PaidCash"]}}},
                  "edges": [{"from": "ask2", "branch": "Unclassified", "to": n1_uuid},
                            {"from": "ask2", "branch": "Paid", "to": n1_uuid}]}],
             manifest_hash="t")
    details = _comp0_details(b)
    assert len(details) == 2  # n1 + ask2, wired without raising


def test_append_custom_branch_unknown_intent_raises():
    b = _bundle_with_intent_and_node()
    n1_uuid = next(iter(_comp0_details(b).keys()))
    with pytest.raises(ValueError, match="not an intent in this export"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "ask2", "prompt": "Paid?",
                               "config": {"branch_intents": {"Paid": ["NoSuchIntent"]}}},
                      "edges": [{"from": "ask2", "branch": "Unclassified", "to": n1_uuid}]}],
                 manifest_hash="t")


def test_append_custom_branch_missing_unclassified_raises():
    b = _bundle_with_intent_and_node()
    n1_uuid = next(iter(_comp0_details(b).keys()))
    with pytest.raises(ValueError, match="no connected Unclassified"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "ask2", "prompt": "Paid?",
                               "config": {"branch_intents": {"Paid": ["PaidCash"]}}},
                      "edges": [{"from": "ask2", "branch": "Paid", "to": n1_uuid}]}],
                 manifest_hash="t")


def test_append_plain_talk_node_unaffected():
    """A plain talk-node append (no branch_intents) behaves exactly as before."""
    b = _load()
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "greet", "prompt": "Greeting"}}], manifest_hash="t")
    assert len(_comp0_details(b)) == 1


def test_append_custom_branch_system_collision_raises():
    b = _bundle_with_intent_and_node()
    n1_uuid = next(iter(_comp0_details(b).keys()))
    with pytest.raises(ValueError, match="collides"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "ask2", "prompt": "Paid?",
                               "config": {"branch_intents": {"Negative": ["PaidCash"]}}},
                      "edges": [{"from": "ask2", "branch": "Negative", "to": n1_uuid},
                                {"from": "ask2", "branch": "Unclassified", "to": n1_uuid}]}],
                 manifest_hash="t")


def test_add_component_custom_branch_missing_unclassified_raises():
    """A talk node in an add-component op with branch_intents but no Unclassified
    edge must raise, mirroring append-node's guard (Finding 2)."""
    b = _load()
    run_mods(b, [{"op": "add-intent", "name": "PaidCash"}], manifest_hash="t")
    with pytest.raises(ValueError, match="no connected Unclassified"):
        run_mods(b, [{"op": "add-component", "name": "NewComponent",
                      "nodes": [
                          {"id": "n1", "prompt": "First"},
                          {"id": "ask", "prompt": "Paid?",
                           "config": {"branch_intents": {"Paid": ["PaidCash"]}}},
                      ],
                      "edges": [{"from": "ask", "branch": "Paid", "to": "n1"}]}],
                 manifest_hash="t")
