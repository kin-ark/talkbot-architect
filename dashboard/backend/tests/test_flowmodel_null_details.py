"""Regression: a component whose details/routes is the JSON string "null"
(real WIZ exports emit `details: "null"` for empty/template components) must
not crash build_components — it should yield a component with zero nodes."""
from flowmodel import build_components


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
