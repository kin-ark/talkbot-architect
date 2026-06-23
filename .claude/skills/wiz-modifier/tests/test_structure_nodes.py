"""TDD test for Task 5: populate_details and add_component use the real node shape.

Run failing (RED) before rewriting structure.py, then GREEN after.
"""

import json
import sys
from pathlib import Path

# wiz-builder's scripts dir must be on sys.path for wizbuilder imports.
_SKILL_ROOT = Path(__file__).resolve().parents[3]  # .claude/
_WB_SCRIPTS = _SKILL_ROOT / "skills" / "wiz-builder" / "scripts"
if str(_WB_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_WB_SCRIPTS))

from wizbuilder.ids import IdMinter  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops import structure  # noqa: E402
from wizmodifier.ops._bsc import get_components  # noqa: E402
from wizmodifier.ops.structure import populate_details  # noqa: E402

BASE = _SKILL_ROOT / "skills" / "wiz-builder" / "templates" / "empty_dialogue.json"


def test_populate_details_emits_real_node(tmp_path):
    data = json.loads(BASE.read_text(encoding="utf-8"))
    bundle = InputBundle(data=data, speech_name="s.json")
    populate_details(bundle, {
        "component": 0,
        "nodes": [{"id": "a", "prompt": "AAA"}, {"id": "b", "prompt": "BBB"}],
        "edges": [{"from": "a", "branch": "Unclassified", "to": "b"}],
    }, IdMinter("h"))
    comp = get_components(bundle)[0]
    node = next(iter(json.loads(comp["details"]).values()))
    assert "data" in node
    assert json.loads(comp["routes"]) and json.loads(comp["inboundPorts"])
    assert len(json.loads(bundle.data["SentenceCutSpeech"])) == 2


def test_populate_details_emits_data_block_with_dialog_list():
    """The 'data' block must have dialog_list with the prompt text."""
    data = json.loads(BASE.read_text(encoding="utf-8"))
    bundle = InputBundle(data=data, speech_name="s.json")
    structure.populate_details(bundle, {
        "component": 0,
        "nodes": [{"id": "x", "prompt": "Hello world"}],
    }, IdMinter("t1"))
    comp = get_components(bundle)[0]
    details = json.loads(comp["details"])
    node = next(iter(details.values()))
    assert "data" in node
    assert node["data"]["dialog_list"][0]["text"] == "Hello world"


def test_populate_details_routes_wired_for_edge():
    """An edge from a to b via Unclassified must produce a non-empty routes entry for a."""
    data = json.loads(BASE.read_text(encoding="utf-8"))
    bundle = InputBundle(data=data, speech_name="s.json")
    structure.populate_details(bundle, {
        "component": 0,
        "nodes": [{"id": "a", "prompt": "First"}, {"id": "b", "prompt": "Second"}],
        "edges": [{"from": "a", "branch": "Positive", "to": "b"}],
    }, IdMinter("t2"))
    comp = get_components(bundle)[0]
    details = json.loads(comp["details"])
    routes = json.loads(comp["routes"])
    # node "a" is entry node (no incoming edge), "b" is not
    node_uuids = list(details.keys())
    assert len(node_uuids) == 2
    # At least one route entry must be non-empty (the edge wiring for "a")
    non_empty_routes = [v for v in routes.values() if v]
    assert len(non_empty_routes) == 1


def test_populate_details_appends_sentence_cut_speech():
    """SentenceCutSpeech must accumulate one row per node."""
    data = json.loads(BASE.read_text(encoding="utf-8"))
    # Prepopulate with one existing row to check appending
    data["SentenceCutSpeech"] = json.dumps(
        [{"existing": True}], ensure_ascii=False, separators=(",", ":")
    )
    bundle = InputBundle(data=data, speech_name="s.json")
    structure.populate_details(bundle, {
        "component": 0,
        "nodes": [{"id": "p", "prompt": "P"}, {"id": "q", "prompt": "Q"}],
    }, IdMinter("t3"))
    scs = json.loads(bundle.data["SentenceCutSpeech"])
    assert len(scs) == 3  # 1 pre-existing + 2 new


def test_add_component_with_nodes_emits_real_shape():
    """add_component with nodes must emit the real node shape (has 'data' key)."""
    data = json.loads(BASE.read_text(encoding="utf-8"))
    bundle = InputBundle(data=data, speech_name="s.json")
    structure.add_component(bundle, {
        "name": "Canvas 2",
        "nodes": [{"id": "r", "prompt": "Root"}],
    }, IdMinter("t4"))
    comps = get_components(bundle)
    new_comp = comps[-1]
    assert new_comp["details"] != "null"
    details = json.loads(new_comp["details"])
    node = next(iter(details.values()))
    assert "data" in node
    assert node["data"]["dialog_list"][0]["text"] == "Root"


def test_add_component_without_nodes_keeps_null():
    """add_component without nodes must leave details as the string 'null'."""
    data = json.loads(BASE.read_text(encoding="utf-8"))
    bundle = InputBundle(data=data, speech_name="s.json")
    structure.add_component(bundle, {"name": "Empty"}, IdMinter("t5"))
    comps = get_components(bundle)
    assert comps[-1]["details"] == "null"



def test_populate_details_raises_on_missing_component_uuid():
    """A component without componentUuid cannot have nodes wired to it — raise, not write ''."""
    import pytest
    data = json.loads(BASE.read_text(encoding="utf-8"))
    comps = json.loads(data["BizSpeechComponent"])
    comps[0].pop("componentUuid", None)
    data["BizSpeechComponent"] = json.dumps(comps)
    bundle = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="componentUuid"):
        populate_details(bundle, {"component": 0, "nodes": [{"id": "a", "prompt": "AAA"}]},
                         IdMinter("h"))
