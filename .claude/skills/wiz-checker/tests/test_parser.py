"""Tests for wizcheck.parser."""

from __future__ import annotations

from uuid import UUID

import pytest
from wizcheck.ir import WizFile
from wizcheck.parser import ParseError, parse_file


def test_parse_minimal_returns_wizfile(fixture_path):
    wf = parse_file(fixture_path("minimal_valid.json"))
    assert isinstance(wf, WizFile)


def test_parse_minimal_has_one_component(fixture_path):
    wf = parse_file(fixture_path("minimal_valid.json"))
    assert len(wf.components) == 1
    comp = next(iter(wf.components.values()))
    assert comp.uuid == UUID("11111111-1111-4111-8111-111111111111")
    assert comp.category == 1
    assert comp.branch == "dev"


def test_parse_minimal_has_one_variable(fixture_path):
    wf = parse_file(fixture_path("minimal_valid.json"))
    assert 100 in wf.variables
    assert wf.variables[100].name == "Name"
    assert wf.variables[100].text_type == "DEFAULT"


def test_parse_minimal_has_intents(fixture_path):
    wf = parse_file(fixture_path("minimal_valid.json"))
    assert 200 in wf.intents
    assert wf.intents[200].name == "Negative"
    assert wf.intents[200].keywords == ("tidak", "nggak")
    assert 201 in wf.intents
    assert wf.intents[201].name == "Unspecified"


def test_parse_minimal_has_one_utterance(fixture_path):
    wf = parse_file(fixture_path("minimal_valid.json"))
    assert len(wf.utterances) == 1
    u = wf.utterances[0]
    assert u.text == "Halo."
    assert u.referenced_vars == ()  # Task 6 will extract; for now empty


def test_parse_minimal_has_one_audio(fixture_path):
    wf = parse_file(fixture_path("minimal_valid.json"))
    assert 300 in wf.audios
    assert wf.audios[300].name == "Nirmala"


def test_parse_dict_rejects_non_dict_top_level():
    from wizcheck.parser import ParseError, parse_dict
    with pytest.raises(ParseError):
        parse_dict([])  # type: ignore[arg-type]
    with pytest.raises(ParseError):
        parse_dict("not a dict")  # type: ignore[arg-type]


def test_parse_unwraps_nested_details(fixture_path):
    wf = parse_file(fixture_path("nested_details.json"))
    comp = next(iter(wf.components.values()))
    assert len(comp.details.flow_nodes) == 2
    root_uuid = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    child_uuid = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    assert root_uuid in comp.details.flow_nodes
    assert child_uuid in comp.details.flow_nodes
    assert comp.details.root_uuids == (root_uuid,)


def test_parse_flownode_parent_link(fixture_path):
    wf = parse_file(fixture_path("nested_details.json"))
    comp = next(iter(wf.components.values()))
    child = comp.details.flow_nodes[UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")]
    assert child.parent_uuid == UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    assert child.label == "Pitch"
    assert child.sort_index == 1


def test_parse_extracts_variable_refs(fixture_path):
    wf = parse_file(fixture_path("with_variables.json"))
    by_id = {u.id: u for u in wf.utterances}
    u1 = by_id[UUID("11111111-1111-4111-8111-111111111111")]
    # deduplicated, order preserved
    assert u1.referenced_vars == ("Name", "Phone")


def test_parse_no_variable_refs_yields_empty_tuple(fixture_path):
    wf = parse_file(fixture_path("with_variables.json"))
    by_id = {u.id: u for u in wf.utterances}
    u2 = by_id[UUID("33333333-3333-4333-8333-333333333333")]
    assert u2.referenced_vars == ()


def test_parse_malformed_uuid_raises_parse_error(fixture_path):
    with pytest.raises(ParseError) as excinfo:
        parse_file(fixture_path("malformed_uuid.json"))
    assert "BizSpeechComponent.componentUuid" in str(excinfo.value)


def test_parse_unreadable_file_raises_parse_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_file(bad)


def test_parse_missing_required_field_raises_parse_error(tmp_path):
    bad = tmp_path / "missing.json"
    bad.write_text(
        '{"BizSpeechComponent":[{"speechId":1,"category":1,"branch":"dev",'
        '"details":"{\\"list\\":[]}"}],"SpeechVariable":[],"SpeechIntent":[],'
        '"SentenceCutSpeech":[],"SpeechAudio":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ParseError) as excinfo:
        parse_file(bad)
    assert "componentUuid" in str(excinfo.value)


def test_parse_missing_variable_id_raises_parse_error(tmp_path):
    bad = tmp_path / "missing_var_id.json"
    bad.write_text(
        '{"BizSpeechComponent":[],"SpeechVariable":[{"name":"X","textType":"DEFAULT"}],'
        '"SpeechIntent":[],"SentenceCutSpeech":[],"SpeechAudio":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ParseError) as excinfo:
        parse_file(bad)
    assert "SpeechVariable" in str(excinfo.value)
    assert "id" in str(excinfo.value)


def test_parse_populates_flow_graph(fixture_path):
    wf = parse_file(fixture_path("nested_details.json"))
    root_uuid = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    child_uuid = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    assert root_uuid in wf.flow.all_nodes()
    assert child_uuid in wf.flow.all_nodes()
    assert wf.flow.reachable_from(root_uuid) == {root_uuid, child_uuid}


def test_parse_detects_orphan_parent(fixture_path):
    wf = parse_file(fixture_path("flow_with_orphans.json"))
    orphan = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
    assert orphan in wf.flow.orphan_refs()


def test_parse_unwrap_list_handles_json_string_blob(tmp_path):
    """Real WIZ files JSON-encode top-level collection values as strings."""
    payload = {
        "BizSpeechComponent": [],
        "SpeechVariable": '[{"id": 99, "name": "X", "textType": "DEFAULT", "type": 0}]',
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }
    import json as _json
    p = tmp_path / "string_collections.json"
    p.write_text(_json.dumps(payload), encoding="utf-8")
    wf = parse_file(p)
    assert 99 in wf.variables
    assert wf.variables[99].name == "X"


def test_parse_real_format_details_uuid_keyed():
    """Real BizSpeechComponent.details uses UUID-keyed envelopes with nested canvas."""
    from wizcheck.parser import parse_dict
    real_format_details = {
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
            "canvas": {
                "component": {
                    "props": {
                        "list": [
                            {"uuid": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                             "parentId": "", "label": "Real Root", "sortIndex": 0}
                        ]
                    }
                }
            }
        }
    }
    import json as _json
    payload = {
        "BizSpeechComponent": [{
            "componentUuid": "11111111-1111-4111-8111-111111111111",
            "speechId": 1, "category": 1, "branch": "dev",
            "details": _json.dumps(real_format_details),
        }],
        "SpeechVariable": [],
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }
    wf = parse_dict(payload)
    comp = next(iter(wf.components.values()))
    real_root = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    assert real_root in comp.details.flow_nodes
    # parentId "" should be treated as root
    assert real_root in comp.details.root_uuids


def test_parse_parent_id_empty_string_treated_as_root():
    """parentId='' is treated as 'no parent' like None."""
    from wizcheck.parser import _parse_component_details

    legacy_with_empty_parent = (
        '{"list":[{"uuid":"cccccccc-cccc-4ccc-8ccc-cccccccccccc",'
        '"parentId":"","label":"Root","sortIndex":0}]}'
    )
    details = _parse_component_details(legacy_with_empty_parent)
    root_uuid = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    assert root_uuid in details.root_uuids
    assert details.flow_nodes[root_uuid].parent_uuid is None


def test_parse_unwrap_list_malformed_string_raises_parse_error():
    """Malformed JSON in a string-encoded collection raises ParseError, not silent failure."""
    import tempfile

    payload_text = (
        '{"BizSpeechComponent":[],"SpeechVariable":"[{not valid json",'
        '"SpeechIntent":[],"SentenceCutSpeech":[],"SpeechAudio":[]}'
    )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(payload_text)
        path = f.name
    with pytest.raises(ParseError):
        parse_file(path)
