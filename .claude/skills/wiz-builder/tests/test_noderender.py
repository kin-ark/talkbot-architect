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


# ---------------------------------------------------------------------------
# Task 2: exit (type 2) + transfer (type 13) node builders
# ---------------------------------------------------------------------------

_BRANCH_IDS = {"Positive": 1, "Negative": 2, "Reject": 3, "Unclassified": 4, "No answer": 5}

def _render_exit(node_type: str, **kw):
    """Helper: render a single Talk(entry) -Unclassified-> exit/transfer node pair."""
    return render_component_nodes(
        [NodeSpec(id="entry", prompt="Hello"), NodeSpec(id="ex", prompt="Goodbye", type=node_type)],
        [EdgeSpec(src="entry", branch="Unclassified", dst="ex")],
        canvas_index=0,
        comp_uuid="comp-u",
        speech_id=8309,
        branch_intent_ids=_BRANCH_IDS,
        kb_ids=["kb1", "kb2"],
        node_language="3",
        minter=IdMinter("h"),
        **kw,
    )


def test_exit_node_type_2_envelope():
    """Exit node has envelope type=2 and data.type=2."""
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    node = r.details[ex_uuid]
    assert node["type"] == 2
    assert node["data"]["type"] == 2
    assert node["data"]["is_transfer"] == 0
    assert node["name"] == "Exit Node"


def test_exit_node_is_terminal_no_ports():
    """Exit node canvas has NO 'ports' key (terminal)."""
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    assert "ports" not in r.details[ex_uuid]["canvas"]


def test_exit_node_routes_empty():
    """Exit node has routes[uuid]={} — no outgoing edges."""
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    assert r.routes[ex_uuid] == {}


def test_exit_node_not_in_inbound_ports():
    """Exit node is NOT an entry node and must not appear in inbound_ports."""
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    inbound_uuids = [p["uuid"] for p in r.inbound_ports]
    assert ex_uuid not in inbound_uuids


def test_exit_node_dialog_text_from_prompt():
    """Exit node carries prompt text in data.dialog_list, data.list, and data.name."""
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    node = r.details[ex_uuid]
    assert node["data"]["dialog_list"][0]["text"] == "Goodbye"
    assert node["data"]["list"] == ["Goodbye"]


def test_exit_node_data_keys_match_fixture():
    """Exit node data keys must match the ground-truth fixture set."""
    fixture_data_keys = {
        "appoint_node_id", "speakType", "hitKnowledgeRate", "intention_judgment_time",
        "type", "repeat_script_type", "hot_words_list", "hangupRate", "exclusive_key_words",
        "dialog_list", "tag_list", "openUserPauseDuration", "can_be_interrupted", "id",
        "node_repetition", "open_pause_duration", "selected", "hitKnowledgeCountsRate",
        "multiple_appoint_id", "openChasingDedayTim", "allow_jump_knowledges_switch",
        "allow_jump_knowledges", "is_transfer", "appoint_knowledge_id", "list", "is_default",
        "textareaList", "nodeLabelArr", "node_language", "agent_type", "tts_language",
        "sms_id", "can_interrupt_percent", "name", "notices_info", "notice_send_type",
        "position",
    }
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    assert set(r.details[ex_uuid]["data"]) == fixture_data_keys


def test_exit_node_canvas_keys_match_fixture():
    """Exit node canvas keys must match the ground-truth fixture set (no 'ports')."""
    fixture_canvas_keys = {
        "view", "component", "size", "shape", "id", "position", "zIndex",
    }
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    assert set(r.details[ex_uuid]["canvas"]) == fixture_canvas_keys


def test_exit_node_top_floor_details_row():
    """Rendering an exit node produces one topFloorDetails row with the node's data."""
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    assert len(r.top_floor_details) == 1
    row = r.top_floor_details[0]
    assert row["id"] == ex_uuid
    assert row["type"] == 2
    assert row["is_transfer"] == 0
    assert row["dialog_list"][0]["text"] == "Goodbye"


def test_exit_node_allows_jump_knowledges():
    """Exit node allow_jump_knowledges = kb_ids passed in."""
    r = _render_exit("exit")
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    assert r.details[ex_uuid]["data"]["allow_jump_knowledges"] == ["kb1", "kb2"]


def test_transfer_node_type_13_envelope():
    """Transfer node has envelope type=13, data.type=13, is_transfer=1, agent_group=1."""
    r = _render_exit("transfer")
    tr_uuid = next(k for k, v in r.details.items() if v["type"] == 13)
    node = r.details[tr_uuid]
    assert node["type"] == 13
    assert node["data"]["type"] == 13
    assert node["data"]["is_transfer"] == 1
    assert node["data"]["agent_group"] == 1


def test_transfer_node_is_terminal_no_ports():
    """Transfer node canvas has NO 'ports' key (terminal)."""
    r = _render_exit("transfer")
    tr_uuid = next(k for k, v in r.details.items() if v["type"] == 13)
    assert "ports" not in r.details[tr_uuid]["canvas"]


def test_transfer_node_routes_empty():
    """Transfer node has routes[uuid]={} — no outgoing edges."""
    r = _render_exit("transfer")
    tr_uuid = next(k for k, v in r.details.items() if v["type"] == 13)
    assert r.routes[tr_uuid] == {}


def test_transfer_node_top_floor_details_empty():
    """Transfer node (type 13) does NOT add a topFloorDetails row (fixture 26 confirms [])."""
    r = _render_exit("transfer")
    assert r.top_floor_details == []


def test_transfer_node_data_keys_match_fixture():
    """Transfer node data keys must match the ground-truth fixture set (exit + agent_group)."""
    fixture_data_keys = {
        "agent_group",
        "appoint_node_id", "speakType", "hitKnowledgeRate", "intention_judgment_time",
        "type", "repeat_script_type", "hot_words_list", "hangupRate", "exclusive_key_words",
        "dialog_list", "tag_list", "openUserPauseDuration", "can_be_interrupted", "id",
        "node_repetition", "open_pause_duration", "selected", "hitKnowledgeCountsRate",
        "multiple_appoint_id", "openChasingDedayTim", "allow_jump_knowledges_switch",
        "allow_jump_knowledges", "is_transfer", "appoint_knowledge_id", "list", "is_default",
        "textareaList", "nodeLabelArr", "node_language", "agent_type", "tts_language",
        "sms_id", "can_interrupt_percent", "name", "notices_info", "notice_send_type",
        "position",
    }
    r = _render_exit("transfer")
    tr_uuid = next(k for k, v in r.details.items() if v["type"] == 13)
    assert set(r.details[tr_uuid]["data"]) == fixture_data_keys


def test_talk_node_unchanged_with_terminal_peer():
    """Talk node output (data keys, ports, routes shape) is unchanged with an exit peer."""
    r = _render_exit("exit")
    talk_uuid = next(k for k, v in r.details.items() if v["type"] == 1)
    talk = r.details[talk_uuid]
    # Talk node has ports
    assert "ports" in talk["canvas"]
    # Talk node is entry
    assert talk["is_default"] is True
    assert any(p["uuid"] == talk_uuid for p in r.inbound_ports)
    # Talk node has outgoing route to the exit node
    assert len(r.routes[talk_uuid]) == 1


def test_no_exit_nodes_top_floor_details_empty():
    """Canvas with only Talk nodes returns empty top_floor_details."""
    r = render_component_nodes(
        [NodeSpec(id="a", prompt="A"), NodeSpec(id="b", prompt="B")],
        [EdgeSpec(src="a", branch="Unclassified", dst="b")],
        canvas_index=0, comp_uuid="c", speech_id=1,
        branch_intent_ids=_BRANCH_IDS, kb_ids=[], node_language="3", minter=IdMinter("h"),
    )
    assert r.top_floor_details == []


def test_exit_node_emits_scs_row():
    """Talk→exit render produces 2 SCS rows; exit row has correct sentenceText and id."""
    r = _render_exit("exit")
    assert len(r.sentence_cut_speech) == 2
    ex_uuid = next(k for k, v in r.details.items() if v["type"] == 2)
    ex_scs = next(row for row in r.sentence_cut_speech if row["id"] == ex_uuid)
    assert ex_scs["sentenceText"] == "Goodbye"
    assert ex_scs["id"] == ex_uuid
    assert ex_scs["type"] == "record"
    assert UUID_RE.fullmatch(ex_scs["speechRecCutId"])


def test_transfer_node_emits_scs_row():
    """Talk→transfer render produces 2 SCS rows; transfer row has correct sentenceText and id."""
    r = _render_exit("transfer")
    assert len(r.sentence_cut_speech) == 2
    tr_uuid = next(k for k, v in r.details.items() if v["type"] == 13)
    tr_scs = next(row for row in r.sentence_cut_speech if row["id"] == tr_uuid)
    assert tr_scs["sentenceText"] == "Goodbye"
    assert tr_scs["id"] == tr_uuid
    assert tr_scs["type"] == "record"
    assert UUID_RE.fullmatch(tr_scs["speechRecCutId"])
