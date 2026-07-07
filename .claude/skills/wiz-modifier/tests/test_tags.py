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
