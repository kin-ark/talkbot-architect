"""Regression: a component whose details/routes is the JSON string "null"
(real WIZ exports emit `details: "null"` for empty/template components) must
not crash build_components — it should yield a component with zero nodes."""
from wizcheck.flowmodel import _build_kbs, build_components


def test_null_string_details_yields_empty_component():
    data = {
        "BizSpeechComponent": [
            {"componentUuid": "c1", "name": "Empty", "details": "null", "routes": "null"},
            {
                "componentUuid": "c2",
                "name": "Greeting",
                "details": {"n1": {"type": 1, "name": "Talk", "is_default": True, "data": {}}},
                "routes": {},
            },
        ]
    }
    comps = build_components(data)
    by_uuid = {c.uuid: c for c in comps}
    assert by_uuid["c1"].nodes == {}        # empty component, no crash
    assert by_uuid["c1"].entry_uuid is None
    assert len(by_uuid["c2"].nodes) == 1    # normal component still parsed


def test_missing_and_none_collections_are_safe():
    # details/routes absent, and BizSpeechComponent itself a "null" string
    assert build_components({"BizSpeechComponent": "null"}) == []
    comps = build_components({"BizSpeechComponent": [{"componentUuid": "c3", "name": "X"}]})
    assert comps[0].nodes == {}


def test_messy_node_data_does_not_crash():
    # Nodes with null data, list-as-string, non-list node_variables, junk KB ids,
    # and a non-dict envelope must all be tolerated.
    data = {
        "BizSpeechComponent": [{
            "componentUuid": "c1", "name": "Messy",
            "details": {
                "n1": {"type": 1, "name": "NullData", "data": None},
                "n2": {
                    "type": 1, "name": "StrList",
                    "data": {"list": "oops", "node_variables": "x",
                             "allow_jump_knowledges": ["7", "bad", 9]},
                },
                "n3": "not-a-dict-envelope",
            },
            "routes": "null",
        }]
    }
    comps = build_components(data)
    nodes = comps[0].nodes
    assert set(nodes) == {"n1", "n2", "n3"}
    assert nodes["n2"].allowed_kbs == [7, 9]   # junk "bad" dropped
    assert nodes["n1"].text == ""


def test_kb_with_string_kdinfo_entries_does_not_crash():
    # Real exports can have kdInfo entries that are plain strings, not dicts,
    # and kdInfo/intents may be JSON-encoded strings.
    data = {
        "BizKnowledgeInfo": [
            {"knowledgeId": 1, "kdTitle": "A", "kdType": 0, "kdInfo": ["just a string", "another"]},
            {"knowledgeId": 2, "kdTitle": "B", "kdInfo": "null", "intents": "null"},
            {"knowledgeId": "3", "kdTitle": "C", "intents": [{"intentId": "42"}]},
            "not-a-dict",
        ]
    }
    kbs = _build_kbs(data)
    by_id = {k.knowledge_id: k for k in kbs}
    assert set(by_id) == {1, 2, 3}        # string kb skipped, others parsed
    assert by_id[1].multi_round is None
    assert by_id[3].intents == [42]       # string intentId coerced to int
