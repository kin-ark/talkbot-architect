import json

from wizcheck.parser import parse_dict


def _bot_with_tags():
    speech_tag = [
        {"id": 100, "name": "Debt Result", "isMutex": 1, "type": 0, "tagProperty": 0,
         "bizTagPropertyDTOS": [
             {"id": 101, "tagId": 100, "value": "Refuse Payment"},
             {"id": 102, "tagId": 100, "value": "Willing to Repay"}]},
        {"id": 200, "name": "Payment Method", "isMutex": 0, "type": 3, "tagProperty": 0,
         "bizTagPropertyDTOS": [{"id": 201, "tagId": 200, "value": ""}]},
    ]
    return {
        "SpeechTag": json.dumps(speech_tag),
        "SpeechVariable": "[]", "SpeechIntent": "[]", "SentenceCutSpeech": "[]",
        "SpeechAudio": "[]", "BizSpeechComponent": "[]", "BizKnowledgeInfo": "[]",
    }


def test_parse_speech_tag_into_ir():
    wf = parse_dict(_bot_with_tags())
    assert len(wf.tags) == 2
    cat = {c.id: c for c in wf.tags}
    assert set(cat) == {"100", "200"}
    debt = cat["100"]
    assert debt.name == "Debt Result"
    assert debt.is_mutex == 1
    assert debt.type == 0
    assert {v.id for v in debt.values} == {"101", "102"}
    v = next(v for v in debt.values if v.id == "101")
    assert v.value == "Refuse Payment"
    assert v.tag_id == "100"


def test_parse_empty_speech_tag():
    raw = _bot_with_tags()
    raw["SpeechTag"] = "[]"
    wf = parse_dict(raw)
    assert wf.tags == ()


def test_parse_missing_speech_tag():
    raw = _bot_with_tags()
    del raw["SpeechTag"]
    wf = parse_dict(raw)
    assert wf.tags == ()


from wizcheck.checks import run_all_checks
from wizcheck.checks.tags import check_tags


def _codes(findings):
    return sorted(f.code for f in findings)


def _comp_with_tag_list(tag_list):
    """A BizSpeechComponent JSON-string with one node carrying data.tag_list."""
    details = {"node-1": {"type": 1, "data": {"name": "Talk Node", "tag_list": tag_list}}}
    return json.dumps([{
        "componentUuid": "00000000-0000-0000-0000-000000000001", "name": "Main",
        "details": json.dumps(details), "routes": "{}", "inboundPorts": "[]",
    }])


def _embedded_category(cat_id, values):
    """Denormalized node tag_list entry: category header + selected value rows."""
    return {
        "id": cat_id, "name": "Debt Result", "isMutex": 1, "type": 0,
        "bizTagPropertyDTOS": [
            {"id": vid, "tagId": tid, "value": "X", "active": True} for vid, tid in values
        ],
    }


def test_resolve_clean_node_and_kbtag():
    raw = _bot_with_tags()
    raw["BizSpeechComponent"] = _comp_with_tag_list(
        [_embedded_category("100", [("101", "100")])])
    raw["kbTag"] = [100, 200]
    wf = parse_dict(raw)
    assert check_tags(wf) == []


def test_wiz401_dangling_category():
    raw = _bot_with_tags()
    raw["BizSpeechComponent"] = _comp_with_tag_list(
        [_embedded_category("999", [("101", "100")])])  # category 999 absent
    wf = parse_dict(raw)
    assert _codes(check_tags(wf)) == ["WIZ401"]


def test_wiz401_unknown_value():
    raw = _bot_with_tags()
    raw["BizSpeechComponent"] = _comp_with_tag_list(
        [_embedded_category("100", [("777", "100")])])  # value 777 absent
    wf = parse_dict(raw)
    assert _codes(check_tags(wf)) == ["WIZ401"]


def test_wiz401_wrong_parent():
    raw = _bot_with_tags()
    # value 201 belongs to category 200, but embedded under category 100
    raw["BizSpeechComponent"] = _comp_with_tag_list(
        [_embedded_category("100", [("201", "100")])])
    wf = parse_dict(raw)
    assert _codes(check_tags(wf)) == ["WIZ401"]


def test_wiz401_omitted_tagid_not_flagged():
    """A valid value whose row OMITS tagId should not flag WIZ401.

    This tests the fix for the wrong-parent predicate false-positive:
    the row clause now gates on presence (only fires when tagId is present).
    """
    raw = _bot_with_tags()
    # Create a category with a value row that omits the tagId key
    details = {"node-1": {"type": 1, "data": {"name": "Talk Node", "tag_list": [
        {
            "id": "100", "name": "Debt Result", "isMutex": 1, "type": 0,
            "bizTagPropertyDTOS": [
                {"id": "101", "value": "Refuse Payment", "active": True}  # tagId omitted
            ],
        }
    ]}}}
    raw["BizSpeechComponent"] = json.dumps([{
        "componentUuid": "00000000-0000-0000-0000-000000000001", "name": "Main",
        "details": json.dumps(details), "routes": "{}", "inboundPorts": "[]",
    }])
    wf = parse_dict(raw)
    # Should not flag WIZ401 because the value 101 is valid under category 100
    # and the missing tagId in the row should not trigger a false positive
    assert check_tags(wf) == []


def test_wiz402_unknown_kbtag():
    raw = _bot_with_tags()
    raw["kbTag"] = [100, 555]  # 555 absent
    wf = parse_dict(raw)
    assert _codes(check_tags(wf)) == ["WIZ402"]


def test_kbtag_tolerant_of_zero_and_none():
    raw = _bot_with_tags()
    raw["kbTag"] = 0
    assert check_tags(parse_dict(raw)) == []
    raw["kbTag"] = "0"
    assert check_tags(parse_dict(raw)) == []


def test_empty_tags_no_findings():
    raw = _bot_with_tags()
    raw["SpeechTag"] = "[]"
    wf = parse_dict(raw)
    assert check_tags(wf) == []


def test_run_all_checks_includes_tags():
    raw = _bot_with_tags()
    raw["BizSpeechComponent"] = _comp_with_tag_list(
        [_embedded_category("999", [("101", "100")])])
    findings = run_all_checks(parse_dict(raw))
    assert any(f.code == "WIZ401" for f in findings)


def test_component_mode_suppresses_tag_findings():
    # A component-export envelope; even if it had tag refs, WIZ401/402 are bot-scope.
    comp_export = {
        "componentImportAndExportDTOS": [{
            "componentName": "Main", "componentUuid": "00000000-0000-0000-0000-000000000001",
            "speechComponentDTO": {
                "componentUuid": "00000000-0000-0000-0000-000000000001", "name": "Main",
                "details": {"node-1": {"type": 1, "data": {
                    "name": "T", "tag_list": [_embedded_category("999", [("101", "100")])]}}},
                "routes": {}, "inboundPorts": [],
            },
            "sentenceCutDTOList": [],
        }],
        "speechIntentDTO": [], "speechVariableDTO": [],
        "speechEntiEntityList": [], "speechEntityData": [],
        "speechFunctionDTO": [], "tagDTOList": [],
    }
    findings = run_all_checks(parse_dict(comp_export))
    assert not any(f.code in ("WIZ401", "WIZ402") for f in findings)
