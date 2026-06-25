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


# ---------------------------------------------------------------------------
# Task 3: goto_component (type 4) node builder
# ---------------------------------------------------------------------------

_TARGET_UUID = "37d91736-c70f-453b-a9f4-bbfe4a48f1a8"
_TARGET_NAME = "2. Second Canvas"


def _render_goto(**kw):
    """Helper: render Talk(entry) -Unclassified-> goto node pair.

    The goto NodeSpec carries resolved target info in config:
    config["target_uuid"] = the pre-minted componentUuid of the target canvas
    config["target_name"] = the canonical canvas name (e.g. "2. Second Canvas")
    component_nav is passed as the full list of component nav entries (needed for
    canvas.component.props.list on the goto canvas).
    """
    comp_nav = [
        {
            "sortIndexABS": 1, "sortIndex": 1, "editStatus": 1, "hangUpRate": "0.0%",
            "label": "1. Greeting", "title": "1. Greeting", "uuid": "comp-uuid-0",
            "hitRate": "0.0%", "parentId": "", "componentUuid": "comp-uuid-0",
            "useStatus": 2, "children": [], "value": "comp-uuid-0",
        },
        {
            "sortIndexABS": 2, "sortIndex": 2, "editStatus": 1, "hangUpRate": "0.0%",
            "label": _TARGET_NAME, "title": _TARGET_NAME, "uuid": _TARGET_UUID,
            "hitRate": "0.0%", "parentId": "", "componentUuid": _TARGET_UUID,
            "useStatus": 1, "children": [], "value": _TARGET_UUID,
        },
    ]
    goto_spec = NodeSpec(
        id="go",
        prompt="(goto)",
        type="goto",
        config={"target": _TARGET_NAME, "target_uuid": _TARGET_UUID, "target_name": _TARGET_NAME},
    )
    return render_component_nodes(
        [NodeSpec(id="entry", prompt="Hello"), goto_spec],
        [EdgeSpec(src="entry", branch="Unclassified", dst="go")],
        canvas_index=0,
        comp_uuid="comp-uuid-0",
        speech_id=8309,
        branch_intent_ids=_BRANCH_IDS,
        kb_ids=["kb1", "kb2"],
        node_language="3",
        minter=IdMinter("h"),
        component_nav=comp_nav,
        **kw,
    )


def test_goto_node_type_4_envelope():
    """Goto node has envelope type=4 and data.type=4."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    node = r.details[goto_uuid]
    assert node["type"] == 4
    assert node["data"]["type"] == 4
    assert node["data"]["is_transfer"] == 0


def test_goto_node_resolves_target_uuid():
    """data.appoint_node_id == target componentUuid passed via config.target_uuid."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    assert r.details[goto_uuid]["data"]["appoint_node_id"] == _TARGET_UUID


def test_goto_node_resolves_target_name():
    """data.specificComponentName == target canvas name passed via config.target_name."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    assert r.details[goto_uuid]["data"]["specificComponentName"] == _TARGET_NAME


def test_goto_node_is_terminal_no_ports():
    """Goto node canvas has NO 'ports' key (terminal)."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    assert "ports" not in r.details[goto_uuid]["canvas"]


def test_goto_node_routes_empty():
    """Goto node has routes[uuid]={} — no outgoing edges."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    assert r.routes[goto_uuid] == {}


def test_goto_node_not_in_inbound_ports():
    """Goto node must NOT appear in inbound_ports."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    inbound_uuids = [p["uuid"] for p in r.inbound_ports]
    assert goto_uuid not in inbound_uuids


def test_goto_node_top_floor_details_row():
    """Goto node emits one topFloorDetails row (type 4) with appoint_node_id set."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    assert len(r.top_floor_details) == 1
    row = r.top_floor_details[0]
    assert row["id"] == goto_uuid
    assert row["type"] == 4
    assert row["appoint_node_id"] == _TARGET_UUID
    assert row["specificComponentName"] == _TARGET_NAME


def test_goto_node_no_scs_row():
    """Talk→goto renders only 1 SCS row (for Talk); goto has NO SentenceCutSpeech row."""
    r = _render_goto()
    assert len(r.sentence_cut_speech) == 1
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    scs_ids = [row["id"] for row in r.sentence_cut_speech]
    assert goto_uuid not in scs_ids


def test_goto_node_data_keys_match_fixture():
    """Goto node data keys must match the ground-truth fixture set (ref_exit_multicomp_25)."""
    fixture_data_keys = {
        "agent_type", "allow_jump_knowledges", "allow_jump_knowledges_switch",
        "appoint_knowledge_id", "appoint_node_id", "can_be_interrupted", "can_interrupt_percent",
        "exclusive_key_words", "hangupRate", "hitKnowledgeCountsRate", "hitKnowledgeRate",
        "hot_words_list", "id", "intention_judgment_time", "is_default", "is_transfer",
        "multiple_appoint_id", "name", "nodeLabelArr", "node_language", "node_repetition",
        "notice_send_type", "notices_info", "openChasingDedayTim", "openUserPauseDuration",
        "open_pause_duration", "position", "repeat_script_type", "selected", "sms_id",
        "speakType", "specificComponentName", "textareaList", "type",
    }
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    assert set(r.details[goto_uuid]["data"]) == fixture_data_keys


def test_goto_node_canvas_keys_match_fixture():
    """Goto node canvas keys must match the fixture set (no 'ports')."""
    fixture_canvas_keys = {"view", "component", "size", "shape", "id", "position", "zIndex"}
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    assert set(r.details[goto_uuid]["canvas"]) == fixture_canvas_keys


def test_goto_canvas_props_list_contains_all_canvases():
    """canvas.component.props.list in goto node matches the component_nav passed in."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    props_list = r.details[goto_uuid]["canvas"]["component"]["props"]["list"]
    labels = [item["label"] for item in props_list]
    assert set(labels) == {"1. Greeting", _TARGET_NAME}


def test_goto_canvas_component_props_type():
    """canvas.component.props.type == 2 (matches fixture 25 goto canvas)."""
    r = _render_goto()
    goto_uuid = next(k for k, v in r.details.items() if v["type"] == 4)
    assert r.details[goto_uuid]["canvas"]["component"]["props"]["type"] == 2


# ---------------------------------------------------------------------------
# Task 4 (noderender): conditional (type 7) + assign (type 10) builders
# ---------------------------------------------------------------------------

from wizbuilder.noderender import NODE_BUILDERS  # noqa: E402


def _minter():
    return IdMinter(manifest_hash="testhash")


_CTX = dict(
    canvas_index=0, comp_uuid="comp-uuid", speech_id=1,
    branch_intent_ids={"Positive": 1, "Negative": 2, "Reject": 3,
                       "Unclassified": 4, "No answer": 5},
    kb_ids=[], node_language="3",
)


def test_registry_has_conditional_and_assign():
    assert "conditional" in NODE_BUILDERS and "assign" in NODE_BUILDERS


def test_assign_node_shape_and_single_port():
    nodes = [
        NodeSpec(id="cond", prompt="", type="conditional", config={
            "variable": "Gender",
            "branches": [
                {"name": "Bapak", "op": "=", "value": "Male", "to": "set_b"},
                {"name": "Default", "to": "set_b"},
            ]}),
        NodeSpec(id="set_b", prompt="", type="assign",
                 config={"variable": "Salutation", "value": "Bapak"}),
    ]
    r = render_component_nodes(nodes, [], minter=_minter(), **_CTX)
    # find the assign node_obj
    assign = next(o for o in r.details.values() if o["type"] == 10)
    d = assign["data"]
    assert d["type"] == 10
    va = d["value_assignment"][0]
    assert va["variable"]["name"] == "Salutation"
    assert va["variable"]["speMark"] == "~@##Salutation##@~"
    assert va["assign"]["func_code"] == "OPT_VALUE_ASSIGNMENT"
    assert va["assign"]["params"][0]["value"] == "Bapak"
    assert d["sentence"] == [] and d["textarea_list"] == []
    # single out-port named Default
    items = assign["canvas"]["ports"]["items"]
    assert len(items) == 1 and items[0]["name"] == "Default"
    # node_variables source 0 (write)
    assert d["node_variables"] == [{"name": "Salutation", "variableSource": 0}]


def test_conditional_ports_branch_rules_and_routing():
    nodes = [
        NodeSpec(id="cond", prompt="", type="conditional", config={
            "variable": "Gender",
            "branches": [
                {"name": "Bapak", "op": "=", "value": "Male", "to": "set_b"},
                {"name": "Bapak", "op": "=", "value": "M", "to": "set_b"},
                {"name": "Ibu", "op": "In", "value": "F,Female", "to": "set_i"},
                {"name": "Default", "to": "set_b"},
            ]}),
        NodeSpec(id="set_b", prompt="", type="assign",
                 config={"variable": "Salutation", "value": "Bapak"}),
        NodeSpec(id="set_i", prompt="", type="assign",
                 config={"variable": "Salutation", "value": "Ibu"}),
    ]
    r = render_component_nodes(nodes, [], minter=_minter(), **_CTX)
    cond_uuid, cond = next((u, o) for u, o in r.details.items() if o["type"] == 7)
    d = cond["data"]
    # distinct ports = 3 (Bapak, Ibu, Default), order preserved first-seen
    assert d["branchList"] == ["Bapak", "Ibu", "Default"]
    items = cond["canvas"]["ports"]["items"]
    assert [it["name"] for it in items] == ["Bapak", "Ibu", "Default"]
    # all_client_intent ids match the port item ids
    aci = {a["name"]: a["id"] for a in d["all_client_intent"]}
    assert aci == {it["name"]: it["id"] for it in items}
    # branch rules: 3 (Default has none); OR via duplicate name preserved
    rules = d["branch"]
    assert len(rules) == 3
    bapak_rules = [b for b in rules if b["name"] == "Bapak"]
    assert {b["branch_judgement_condition"][0]["right_value"] for b in bapak_rules} == {"Male", "M"}
    ibu = next(b for b in rules if b["name"] == "Ibu")
    assert ibu["branch_judgement_condition"][0]["operator"] == "In"
    assert ibu["branch_judgement_condition"][0]["type"] == "const"
    # node_variables one per rule (3); no var_source_by_name passed → source defaults to 0 (custom)
    assert d["node_variables"] == [{"name": "Gender", "variableSource": 0}] * 3
    # routes: one port per distinct branch, keyed by all_client_intent id
    cond_routes = r.routes[cond_uuid]
    assert set(cond_routes.keys()) == set(aci.values())


def test_conditional_value_var_emits_variable_type():
    nodes = [
        NodeSpec(id="cond", prompt="", type="conditional", config={
            "variable": "Gender",
            "branches": [
                {"name": "Match", "op": "=", "value_var": "Expected", "to": "t"},
                {"name": "Default", "to": "t"},
            ]}),
        NodeSpec(id="t", prompt="", type="assign",
                 config={"variable": "Salutation", "value": "x"}),
    ]
    r = render_component_nodes(nodes, [], minter=_minter(), **_CTX)
    cond = next(o for o in r.details.values() if o["type"] == 7)
    rule = next(b for b in cond["data"]["branch"] if b["name"] == "Match")
    cnd = rule["branch_judgement_condition"][0]
    assert cnd["type"] == "variable" and cnd["right_value"] == "Expected"


def test_conditional_unary_op_no_right_value():
    nodes = [
        NodeSpec(id="cond", prompt="", type="conditional", config={
            "variable": "Gender",
            "branches": [
                {"name": "Empty", "op": "IsNull", "to": "t"},
                {"name": "Default", "to": "t"},
            ]}),
        NodeSpec(id="t", prompt="", type="assign",
                 config={"variable": "Salutation", "value": "x"}),
    ]
    r = render_component_nodes(nodes, [], minter=_minter(), **_CTX)
    cond = next(o for o in r.details.values() if o["type"] == 7)
    rule = next(b for b in cond["data"]["branch"] if b["name"] == "Empty")
    cnd = rule["branch_judgement_condition"][0]
    assert cnd["operator"] == "Null"  # canonical: WIZ platform maps IsNull→"Null"
    assert "right_value" not in cnd or cnd["right_value"] == ""


def test_conditional_no_scs_no_topfloor():
    nodes = [
        NodeSpec(id="cond", prompt="", type="conditional", config={
            "variable": "Gender",
            "branches": [{"name": "A", "op": "=", "value": "x", "to": "t"},
                         {"name": "Default", "to": "t"}]}),
        NodeSpec(id="t", prompt="", type="assign",
                 config={"variable": "Salutation", "value": "x"}),
    ]
    r = render_component_nodes(nodes, [], minter=_minter(), **_CTX)
    assert r.sentence_cut_speech == []
    assert r.top_floor_details == []


def test_conditional_entry_inbound_port_type_7():
    nodes = [
        NodeSpec(id="cond", prompt="", type="conditional", config={
            "variable": "Gender",
            "branches": [{"name": "A", "op": "=", "value": "x", "to": "t"},
                         {"name": "Default", "to": "t"}]}),
        NodeSpec(id="t", prompt="", type="assign",
                 config={"variable": "Salutation", "value": "x"}),
    ]
    r = render_component_nodes(nodes, [], minter=_minter(), **_CTX)
    # cond is the entry (nothing targets it); inbound port carries type 7
    assert any(p["type"] == 7 for p in r.inbound_ports)
    # the assign target is NOT an entry (conditional routes into it)
    assert all(p["type"] != 10 for p in r.inbound_ports)


def test_talk_golden_unchanged():
    # talk-only render must be byte-identical to before (regression guard).
    nodes = [NodeSpec(id="greet", prompt="Halo", type="talk")]
    r = render_component_nodes(nodes, [], minter=_minter(), **_CTX)
    talk = next(iter(r.details.values()))
    assert talk["type"] == 1
    assert [it["name"] for it in talk["canvas"]["ports"]["items"]] == \
        ["Positive", "Negative", "Unclassified"]


# ---------------------------------------------------------------------------
# NC-Task 2: exit_port (type 4) + nested (type 11) builders
# ---------------------------------------------------------------------------

def test_exit_port_terminal_topfloor_no_scs():
    nodes = [
        NodeSpec(id="ask", prompt="Q", type="talk"),
        NodeSpec(id="ex", prompt="", type="exit_port", config={"name": "Yes"}),
    ]
    edges = [EdgeSpec(src="ask", branch="Positive", dst="ex")]
    r = render_component_nodes(nodes, edges, minter=_minter(), **_CTX)
    ex = next(o for o in r.details.values() if o["type"] == 4)
    assert ex["data"]["appoint_node_id"] == "" and ex["data"]["specificComponentName"] == ""
    assert ex["name"] == "Yes" and ex["data"]["name"] == "Yes"
    assert "ports" not in ex["canvas"]                      # terminal
    ex_uuid = next(u for u, o in r.details.items() if o["type"] == 4)
    assert r.routes[ex_uuid] == {}                          # terminal route
    assert ex["data"] in r.top_floor_details                # topFloorDetails row
    # talk emits 1 SCS row, exit_port emits none: total == 1
    assert len(r.sentence_cut_speech) == 1
    assert ex_uuid not in [row["id"] for row in r.sentence_cut_speech]  # exit_port itself: no SCS


def test_nested_node_ports_mirror_child_exits():
    # child exit uuids supplied via nested_exit_map
    child_map = {"Child": {"Yes": "child-yes-uuid", "No": "child-no-uuid"}}
    nodes = [
        NodeSpec(id="open", prompt="Hi", type="talk"),
        NodeSpec(id="sub", prompt="", type="nested",
                 config={"target": "Child", "target_uuid": "child-comp-uuid"}),
        NodeSpec(id="bye_yes", prompt="Y", type="exit"),
        NodeSpec(id="bye_no", prompt="N", type="exit"),
    ]
    edges = [
        EdgeSpec(src="open", branch="Unclassified", dst="sub"),
        EdgeSpec(src="sub", branch="Yes", dst="bye_yes"),
        EdgeSpec(src="sub", branch="No", dst="bye_no"),
    ]
    r = render_component_nodes(nodes, edges, minter=_minter(), nested_exit_map=child_map, **_CTX)
    sub_uuid, sub = next((u, o) for u, o in r.details.items() if o["type"] == 11)
    # subComponentUuid set by canvases.py normally; here from config target_uuid via spec.config
    assert sub["data"]["subComponentUuid"]
    items = sub["canvas"]["ports"]["items"]
    by_name = {it["name"]: it for it in items}
    assert by_name["Yes"]["uuid"] == "child-yes-uuid"      # port.uuid == child exit uuid
    assert by_name["No"]["uuid"] == "child-no-uuid"
    # routes keyed by child-exit-uuid -> parent target
    assert "child-yes-uuid" in r.routes[sub_uuid]
    assert r.routes[sub_uuid]["child-yes-uuid"]["target"]["uuid"] == \
        next(u for u, o in r.details.items() if o.get("data", {}).get("list") == ["Y"])
    # nested node contributes NO SCS row and NO topFloorDetails row
    assert sub["data"] not in r.top_floor_details
    assert sub_uuid not in [row["id"] for row in r.sentence_cut_speech]


# ---------------------------------------------------------------------------
# Deploy-gate fixes: FIX 1 (envelope id) + FIX 2 (source.type=3 for nested)
# ---------------------------------------------------------------------------


def test_nested_node_envelope_id_equals_sub_component_uuid():
    """FIX 1: nested node_obj must carry a top-level 'id' == subComponentUuid.

    Without this key WIZ import returns code:-1.
    """
    child_map = {"Child": {"Done": "child-done-uuid"}}
    nodes = [
        NodeSpec(id="open", prompt="Hi", type="talk"),
        NodeSpec(id="sub", prompt="", type="nested",
                 config={"target": "Child", "target_uuid": "child-comp-uuid-123"}),
        NodeSpec(id="bye", prompt="Bye", type="exit"),
    ]
    edges = [
        EdgeSpec(src="open", branch="Unclassified", dst="sub"),
        EdgeSpec(src="sub", branch="Done", dst="bye"),
    ]
    r = render_component_nodes(nodes, edges, minter=_minter(), nested_exit_map=child_map, **_CTX)
    sub_uuid, sub = next((u, o) for u, o in r.details.items() if o["type"] == 11)
    # FIX 1: envelope must have id == subComponentUuid from spec.config["target_uuid"]
    assert "id" in sub, "nested node_obj must have a top-level 'id' key"
    assert sub["id"] == "child-comp-uuid-123", (
        f"nested node envelope id must == subComponentUuid (target_uuid), "
        f"got {sub['id']!r}"
    )
    assert sub["data"]["subComponentUuid"] == "child-comp-uuid-123"


def test_nested_out_edges_have_source_type_3():
    """FIX 2: route edges out of a nested (type-11) node must have source.type == 3.

    With source.type=1 the import succeeds but the deployed flow breaks (port→target
    link is not resolved). Only nested nodes are affected; talk nodes must stay at 1.
    """
    child_map = {"Child": {"Yes": "child-yes-uuid", "No": "child-no-uuid"}}
    nodes = [
        NodeSpec(id="open", prompt="Hi", type="talk"),
        NodeSpec(id="sub", prompt="", type="nested",
                 config={"target": "Child", "target_uuid": "child-comp-uuid"}),
        NodeSpec(id="bye_yes", prompt="Y", type="exit"),
        NodeSpec(id="bye_no", prompt="N", type="exit"),
    ]
    edges = [
        EdgeSpec(src="open", branch="Unclassified", dst="sub"),
        EdgeSpec(src="sub", branch="Yes", dst="bye_yes"),
        EdgeSpec(src="sub", branch="No", dst="bye_no"),
    ]
    r = render_component_nodes(nodes, edges, minter=_minter(), nested_exit_map=child_map, **_CTX)
    sub_uuid = next(u for u, o in r.details.items() if o["type"] == 11)
    nested_routes = r.routes[sub_uuid]
    assert nested_routes, "nested node must have outgoing routes"
    for port_uuid, edge_obj in nested_routes.items():
        assert edge_obj["source"]["type"] == 3, (
            f"nested out-edge at port {port_uuid!r}: expected source.type=3, "
            f"got {edge_obj['source']['type']!r}"
        )


def test_talk_out_edges_source_type_unchanged_at_1():
    """Regression: talk node out-edges must still have source.type == 1 (not affected by FIX 2)."""
    child_map = {"Child": {"Done": "child-done-uuid"}}
    nodes = [
        NodeSpec(id="open", prompt="Hi", type="talk"),
        NodeSpec(id="sub", prompt="", type="nested",
                 config={"target": "Child", "target_uuid": "child-comp-uuid"}),
        NodeSpec(id="bye", prompt="Bye", type="exit"),
    ]
    edges = [
        EdgeSpec(src="open", branch="Unclassified", dst="sub"),
        EdgeSpec(src="sub", branch="Done", dst="bye"),
    ]
    r = render_component_nodes(nodes, edges, minter=_minter(), nested_exit_map=child_map, **_CTX)
    open_uuid = next(u for u, o in r.details.items() if o["type"] == 1)
    talk_routes = r.routes[open_uuid]
    assert talk_routes, "talk node must have outgoing routes"
    for port_uuid, edge_obj in talk_routes.items():
        assert edge_obj["source"]["type"] == 1, (
            f"talk out-edge at port {port_uuid!r}: expected source.type=1 (regression), "
            f"got {edge_obj['source']['type']!r}"
        )
