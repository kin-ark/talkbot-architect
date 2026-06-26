import json
from pathlib import Path

import pytest
from wizmodifier.apply import run_mods
from wizmodifier.io import InputBundle

BASELINE = Path(__file__).resolve().parents[4] / "talkbot" / "Empty+Dialogue.zip"


def _load():
    return InputBundle.load(BASELINE)


def _comp0_details(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    d = comps[0].get("details")
    return json.loads(d) if isinstance(d, str) and d not in ("null", "") else {}


def test_append_into_empty_component_adds_one_node():
    b = _load()
    baseline = len(_comp0_details(b))
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "greet", "prompt": "Greeting"}}], manifest_hash="t")
    assert len(_comp0_details(b)) == baseline + 1


def test_append_preserves_existing_node_uuids():
    b = _load()
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "n1", "prompt": "First"}}], manifest_hash="t")
    before = set(_comp0_details(b).keys())
    # append a second node with an edge from the first (existing) node by uuid
    src_uuid = next(iter(before))
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "n2", "prompt": "Second"},
                  "edges": [{"from": src_uuid, "branch": "Unclassified", "to": "n2"}]}],
             manifest_hash="t")
    after = _comp0_details(b)
    assert before <= set(after.keys())          # every old uuid still present
    assert len(after) == len(before) + 1         # exactly one new node


def test_append_wires_edge_on_existing_source_port():
    b = _load()
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "n1", "prompt": "First"}}], manifest_hash="t")
    src_uuid = next(iter(_comp0_details(b).keys()))
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "n2", "prompt": "Second"},
                  "edges": [{"from": src_uuid, "branch": "Unclassified", "to": "n2"}]}],
             manifest_hash="t")
    comps = json.loads(b.data["BizSpeechComponent"])
    routes = json.loads(comps[0]["routes"])
    # the existing source node now has a route on its Unclassified port
    assert src_uuid in routes
    assert len(routes[src_uuid]) == 1


def test_append_rejects_unknown_edge_branch():
    b = _load()
    with pytest.raises(ValueError):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "n1", "prompt": "First"},
                      "edges": [{"from": "n1", "branch": "Bogus", "to": "n1"}]}],
                 manifest_hash="t")


# ---------------------------------------------------------------------------
# goto_kb tests (Task 2 — modifier: resolve KB name → appoint_knowledge_id)
# The baseline Empty+Dialogue.zip has real BizKnowledgeInfo entries; the first
# one is "Can not hear clearly" (knowledgeId 244811).
# ---------------------------------------------------------------------------

_GOTO_KB_TARGET = "Can not hear clearly"   # real kdTitle from baseline
_GOTO_KB_KID = 244811                       # matching knowledgeId


def _comp0_routes(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    r = comps[0].get("routes")
    return json.loads(r) if isinstance(r, str) and r not in ("null", "") else {}


def _comp0_top_floor(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    tfd = comps[0].get("topFloorDetails")
    return json.loads(tfd) if isinstance(tfd, str) and tfd not in ("null", "") else []


def test_append_goto_kb_node_shape():
    """goto_kb node: type 8, terminal (routes[uuid]=={}), in topFloorDetails,
    appoint_knowledge_id == str(knowledgeId of target KB)."""
    b = _load()
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "jump", "type": "goto_kb", "prompt": "",
                           "config": {"target": _GOTO_KB_TARGET}}}],
             manifest_hash="t")

    details = _comp0_details(b)
    assert len(details) == 1, "expected exactly one node in details"
    node_uuid, node_obj = next(iter(details.items()))

    # type 8
    assert node_obj["data"]["type"] == 8

    # terminal: routes[uuid] must be empty dict (no out-edges)
    routes = _comp0_routes(b)
    assert node_uuid in routes
    assert routes[node_uuid] == {}

    # appoint_knowledge_id is the string form of the resolved knowledgeId
    assert node_obj["data"]["appoint_knowledge_id"] == str(_GOTO_KB_KID)

    # uuid present in topFloorDetails
    tfd = _comp0_top_floor(b)
    tfd_ids = {row.get("id") for row in tfd}
    assert node_uuid in tfd_ids, "goto_kb node uuid must appear in topFloorDetails"


def test_append_goto_kb_unknown_target_raises():
    """goto_kb with an unknown KB name raises ValueError."""
    b = _load()
    with pytest.raises(ValueError, match="not found in BizKnowledgeInfo"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "jump", "type": "goto_kb", "prompt": "",
                               "config": {"target": "NonExistentKB"}}}],
                 manifest_hash="t")


def test_append_goto_kb_missing_target_raises():
    """goto_kb with no config.target raises ValueError (validation gate)."""
    b = _load()
    with pytest.raises(ValueError, match="missing config\\.target"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "jump", "type": "goto_kb", "prompt": "",
                               "config": {}}}],
                 manifest_hash="t")
