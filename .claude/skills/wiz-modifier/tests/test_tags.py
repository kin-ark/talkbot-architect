import json

import pytest

from wizmodifier.floweditor import FlowEditError, FlowEditor


def _component_with_node(uuid="n1"):
    details = {uuid: {"type": 1, "data": {"name": "Talk Node", "tag_list": []}}}
    return {
        "componentUuid": "c1", "name": "Main",
        "details": json.dumps(details), "routes": "{}",
        "inboundPorts": "[]", "topFloorDetails": "[]",
    }


def test_set_tags_sets_and_flushes():
    comp = _component_with_node("n1")
    fe = FlowEditor(comp)
    tl = [{"id": "100", "name": "Debt Result", "bizTagPropertyDTOS": [
        {"id": "101", "tagId": "100", "value": "Willing to Repay", "active": True}]}]
    fe.set_tags("n1", tl)
    fe.flush()
    details = json.loads(comp["details"])
    assert details["n1"]["data"]["tag_list"] == tl


def test_set_tags_empty_clears():
    comp = _component_with_node("n1")
    # pre-seed a tag_list
    d = json.loads(comp["details"]); d["n1"]["data"]["tag_list"] = [{"x": 1}]
    comp["details"] = json.dumps(d)
    fe = FlowEditor(comp)
    fe.set_tags("n1", [])
    fe.flush()
    assert json.loads(comp["details"])["n1"]["data"]["tag_list"] == []


def test_set_tags_unknown_uuid_raises():
    fe = FlowEditor(_component_with_node("n1"))
    with pytest.raises(FlowEditError):
        fe.set_tags("nope", [])


from wizmodifier.io import InputBundle
from wizmodifier.apply import run_mods


def _bundle_with_speechtag(extra_values=True):
    """An export with one component (talk node n1 + exit n2) and a real-ish SpeechTag."""
    import uuid
    c_uuid = str(uuid.uuid4())
    n1_uuid = str(uuid.uuid4())
    n2_uuid = str(uuid.uuid4())
    details = {
        n1_uuid: {"type": 1, "data": {"name": "Talk Node", "tag_list": [], "is_default": True}},
        n2_uuid: {"type": 2, "data": {"name": "Exit Node", "tag_list": []}},
    }
    comp = {
        "componentUuid": c_uuid, "name": "Main", "branch": "dev",
        "details": json.dumps(details), "routes": "{}",
        "inboundPorts": json.dumps([{"nodeId": n1_uuid}]), "topFloorDetails": "[]",
    }
    debt_vals = [
        {"id": 576001, "tagId": 576000, "value": "Refuse Payment"},
        {"id": 576002, "tagId": 576000, "value": "Willing to Repay"},
    ]
    speech_tag = [{
        "id": 576000, "name": "Debt Result", "isMutex": 1, "type": 0, "tagProperty": 0,
        "entId": 289775363934961856, "createTime": 1732252906000, "modifyTime": 1732252906000,
        "bizTagPropertyDTOS": debt_vals if extra_values else debt_vals[:1],
    }]
    return InputBundle(data={
        "BizSpeechComponent": json.dumps([comp]),
        "SpeechTag": json.dumps(speech_tag),
        "SpeechIntent": "[]", "SpeechVariable": "[]", "SentenceCutSpeech": "[]",
        "BizKnowledgeInfo": "[]", "kbTag": [],
    }, speech_name="speech1.json"), n1_uuid


def _tag_finding_codes(bundle):
    from wizcheck.checks import run_all_checks
    from wizcheck.parser import parse_dict
    return [f.code for f in run_all_checks(parse_dict(bundle.data))
            if f.code in ("WIZ401", "WIZ402")]


def _node_tag_list(bundle, node_uuid):
    comp = json.loads(bundle.data["BizSpeechComponent"])[0]
    return json.loads(comp["details"])[node_uuid]["data"]["tag_list"]


def test_set_node_tags_resolves_existing_real_ids():
    b, n1_uuid = _bundle_with_speechtag()
    run_mods(b, [{"op": "set-node-tags", "node": {"uuid": n1_uuid},
                  "tags": [{"category": "Debt Result", "values": ["Willing to Repay"]}]}],
             manifest_hash="h")
    tl = _node_tag_list(b, n1_uuid)
    assert len(tl) == 1
    cat = tl[0]
    assert cat["id"] == "576000"                      # REAL category id, stringified
    rows = cat["bizTagPropertyDTOS"]
    assert len(rows) == 1 and rows[0]["value"] == "Willing to Repay"
    assert rows[0]["id"] == "576002" and rows[0]["active"] is True
    # kbTag now references the category (int)
    assert b.data["kbTag"] == [576000]
    # checker-clean
    from wizcheck.parser import parse_dict
    from wizcheck.checks import run_all_checks
    codes = [f.code for f in run_all_checks(parse_dict(b.data)) if f.code in ("WIZ401", "WIZ402")]
    assert codes == []


def test_set_node_tags_mints_absent_category():
    b, n1_uuid = _bundle_with_speechtag()
    run_mods(b, [{"op": "set-node-tags", "node": {"uuid": n1_uuid},
                  "tags": [{"category": "Person Reached", "values": ["Correct Person"]}]}],
             manifest_hash="h")
    st = json.loads(b.data["SpeechTag"])
    names = {c["name"] for c in st}
    assert "Person Reached" in names                  # appended
    pr = next(c for c in st if c["name"] == "Person Reached")
    assert pr["bizTagPropertyDTOS"][0]["value"] == "Correct Person"
    from wizcheck.parser import parse_dict
    from wizcheck.checks import run_all_checks
    assert [f.code for f in run_all_checks(parse_dict(b.data)) if f.code in ("WIZ401", "WIZ402")] == []


def test_set_node_tags_appends_absent_value_to_existing_category():
    b, n1_uuid = _bundle_with_speechtag(extra_values=False)  # Debt Result has only "Refuse Payment"
    run_mods(b, [{"op": "set-node-tags", "node": {"uuid": n1_uuid},
                  "tags": [{"category": "Debt Result", "values": ["Willing to Repay"]}]}],
             manifest_hash="h")
    st = json.loads(b.data["SpeechTag"])
    debt = next(c for c in st if c["name"] == "Debt Result")
    vals = {p["value"] for p in debt["bizTagPropertyDTOS"]}
    assert "Willing to Repay" in vals                 # appended to existing category
    from wizcheck.parser import parse_dict
    from wizcheck.checks import run_all_checks
    assert [f.code for f in run_all_checks(parse_dict(b.data)) if f.code in ("WIZ401", "WIZ402")] == []


def test_set_node_tags_empty_clears_and_prunes_kbtag():
    b, n1_uuid = _bundle_with_speechtag()
    run_mods(b, [{"op": "set-node-tags", "node": {"uuid": n1_uuid},
                  "tags": [{"category": "Debt Result", "values": ["Willing to Repay"]}]}],
             manifest_hash="h")
    assert b.data["kbTag"] == [576000]
    run_mods(b, [{"op": "set-node-tags", "node": {"uuid": n1_uuid}, "tags": []}], manifest_hash="h")
    assert _node_tag_list(b, n1_uuid) == []
    assert b.data["kbTag"] == []                       # pruned


def test_set_node_tags_unknown_node_raises():
    b, _ = _bundle_with_speechtag()
    with pytest.raises(ValueError):
        run_mods(b, [{"op": "set-node-tags", "node": {"uuid": "zzz"},
                      "tags": [{"category": "Debt Result", "values": ["Willing to Repay"]}]}],
                 manifest_hash="h")


def test_set_node_tags_component_mode_rejected():
    b, n1_uuid = _bundle_with_speechtag()
    b.is_component = True
    with pytest.raises(ValueError, match="component mode"):
        run_mods(b, [{"op": "set-node-tags", "node": {"uuid": n1_uuid},
                      "tags": [{"category": "Debt Result", "values": ["Willing to Repay"]}]}],
                 manifest_hash="h")
