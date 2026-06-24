import json
from pathlib import Path
import pytest
from wizmodifier.io import InputBundle
from wizmodifier.apply import run_mods


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
