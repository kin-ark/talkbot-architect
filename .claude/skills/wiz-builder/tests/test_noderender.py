import json
import re
from pathlib import Path

import pytest
from wizbuilder.ids import IdMinter
from wizbuilder.noderender import EdgeSpec, NodeSpec, render_component_nodes  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def test_single_node_matches_reference_shape():
    ref = json.loads((FIX / "ref_one_node.json").read_text(encoding="utf-8"))
    ref_comp = json.loads(ref["BizSpeechComponent"])[0]
    ref_details = json.loads(ref_comp["details"])
    ref_node = next(iter(ref_details.values()))

    r = render_component_nodes(
        [NodeSpec(id="greet", prompt="Test only")], [],
        canvas_index=0, comp_uuid="comp-uuid", speech_id=8309,
        branch_intent_ids={"Positive": 463428, "Negative": 463429, "Reject": 463430,
                           "Unclassified": 463431, "No answer": 463433},
        kb_ids=["244811"], node_language="3", minter=IdMinter("h"),
    )
    got_node = next(iter(r.details.values()))
    # same top-level node keys
    assert set(got_node) == set(ref_node)
    # same data keys (39) and same canvas keys
    assert set(got_node["data"]) == set(ref_node["data"])
    assert set(got_node["canvas"]) == set(ref_node["canvas"])
    # prompt is carried into dialog_list + SentenceCutSpeech
    assert got_node["data"]["dialog_list"][0]["text"] == "Test only"
    scs = r.sentence_cut_speech[0]
    assert scs["sentenceText"] == "Test only"
    assert scs["type"] == "record" and UUID_RE.fullmatch(scs["speechRecCutId"])
    # leaf node -> empty routes entry, entry node -> inbound port
    nid = next(iter(r.details))
    assert r.routes[nid] == {}
    assert r.inbound_ports == [{"name": "Talk Node", "type": 1, "uuid": nid, "is_default": True}]


def test_edge_wires_routes_and_entry_detection():
    r = render_component_nodes(
        [NodeSpec("a","AAA"), NodeSpec("b","BBB")],
        [EdgeSpec(src="a", branch="Unclassified", dst="b")],
        canvas_index=0, comp_uuid="c", speech_id=8309,
        branch_intent_ids={"Positive":1,"Negative":2,"Reject":3,"Unclassified":4,"No answer":5},
        kb_ids=[], node_language="3", minter=IdMinter("h"),
    )
    a_uuid = next(k for k,v in r.details.items() if v["data"]["dialog_list"][0]["text"]=="AAA")
    b_uuid = next(k for k,v in r.details.items() if v["data"]["dialog_list"][0]["text"]=="BBB")
    # entry detection: a is entry (is_default true, in inbound), b is not
    assert r.details[a_uuid]["is_default"] is True
    assert r.details[b_uuid]["is_default"] is False
    assert [p["uuid"] for p in r.inbound_ports] == [a_uuid]
    # edge in routes under a's Unclassified port -> b
    a_unclass_port = next(p["id"] for p in r.details[a_uuid]["canvas"]["ports"]["items"]
                          if p["name"]=="Unclassified")
    edge = r.routes[a_uuid][a_unclass_port]
    assert edge["source"]["uuid"] == a_unclass_port
    assert edge["target"]["uuid"] == b_uuid
    assert r.routes[b_uuid] == {}


def test_sentence_cut_id_seeded_by_manifest_hash():
    """sentenceCutId must vary by manifest_hash (cross-build uniqueness) yet stay
    deterministic for the same manifest_hash + node seed."""
    common = dict(
        canvas_index=0, comp_uuid="c", speech_id=8309,
        branch_intent_ids={"Positive": 1, "Negative": 2, "Reject": 3,
                           "Unclassified": 4, "No answer": 5},
        kb_ids=[], node_language="3",
    )
    scid = lambda mh: render_component_nodes(  # noqa: E731
        [NodeSpec(id="a", prompt="AAA")], [], minter=IdMinter(mh), **common
    ).sentence_cut_speech[0]["sentenceCutId"]
    a1, a2, a1b = scid("hash-1"), scid("hash-2"), scid("hash-1")
    assert a1 != a2, "different manifest_hash must yield different sentenceCutId"
    assert a1 == a1b, "same manifest_hash must be deterministic"
    assert 0 < a1 < 2 ** 63


def test_unknown_node_type_raises():
    """render_component_nodes must raise ValueError for an unregistered node type."""
    with pytest.raises(ValueError, match="unknown node type"):
        render_component_nodes(
            [NodeSpec(id="n", prompt="P", type="bogus")],
            [],
            canvas_index=0,
            comp_uuid="c",
            speech_id=1,
            branch_intent_ids={"Positive": 1, "Negative": 2, "Reject": 3,
                               "Unclassified": 4, "No answer": 5},
            kb_ids=[],
            node_language="3",
            minter=IdMinter("h"),
        )
