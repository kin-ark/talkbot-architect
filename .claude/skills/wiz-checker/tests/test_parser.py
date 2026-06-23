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
    assert wf.intents[201].name == "Unclassified"


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


def test_parse_nested_details_fixture_parses_cleanly(fixture_path):
    """nested_details.json fixture parses without error and yields one component."""
    wf = parse_file(fixture_path("nested_details.json"))
    assert len(wf.components) == 1


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
    """Real BizSpeechComponent.details uses UUID-keyed envelopes — parses into flow_model."""
    import json as _json

    from wizcheck.parser import parse_dict
    real_format_details = {
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
            "type": 1,
            "name": "Real Root",
            "is_default": True,
            "data": {"list": []},
        }
    }
    payload = {
        "BizSpeechComponent": [{
            "componentUuid": "11111111-1111-4111-8111-111111111111",
            "speechId": 1, "category": 1, "branch": "dev",
            "details": _json.dumps(real_format_details),
            "routes": _json.dumps({}),
        }],
        "SpeechVariable": [],
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }
    wf = parse_dict(payload)
    assert wf.flow_model is not None
    assert len(wf.flow_model.components) == 1
    fc = wf.flow_model.components[0]
    assert "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" in fc.nodes


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



def test_parser_loads_empty_canvas_fixture(fixture_path):
    """End-to-end: empty_canvas.json parses cleanly and yields a zero-node component."""
    wf = parse_file(fixture_path("empty_canvas.json"))
    assert len(wf.components) == 1
    # flow_model should have one component with no nodes (details="null")
    assert wf.flow_model is not None
    assert len(wf.flow_model.components) == 1
    assert wf.flow_model.components[0].nodes == {}


def test_parser_populates_variable_source(tmp_path):
    """SpeechVariable.variableSource is read into Variable.variable_source."""
    import json as _json
    payload = {
        "BizSpeechComponent": [],
        "SpeechVariable": [
            {"id": 1, "name": "UserVar", "textType": "", "type": 0, "variableSource": 0},
            {"id": 2, "name": "SystemVar", "textType": "DEFAULT", "type": 0, "variableSource": 1},
        ],
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }
    p = tmp_path / "varsource.json"
    p.write_text(_json.dumps(payload), encoding="utf-8")
    wf = parse_file(p)
    assert wf.variables[1].variable_source == 0
    assert wf.variables[2].variable_source == 1


def test_parser_variable_source_defaults_to_zero(tmp_path):
    """Missing variableSource field defaults to 0 (user-authored)."""
    import json as _json
    payload = {
        "BizSpeechComponent": [],
        "SpeechVariable": [
            {"id": 1, "name": "NoSourceField", "textType": ""},
        ],
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }
    p = tmp_path / "no_source.json"
    p.write_text(_json.dumps(payload), encoding="utf-8")
    wf = parse_file(p)
    assert wf.variables[1].variable_source == 0


def test_parse_dict_attaches_flow_model(tmp_path):
    from wizcheck.parser import parse_dict
    data = {
        "BizSpeechComponent": [
            {
                "componentUuid": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                "name": "x", "details": "null",
            }
        ],
        "SpeechVariable": "[]",
        "SpeechIntent": "[]",
    }
    wf = parse_dict(data)
    assert hasattr(wf, "flow_model")
    assert wf.flow_model.components[0].name == "x"


def test_parse_knowledge_bases(tmp_path):
    import json as _json
    payload = {
        "BizSpeechComponent": [],
        "SpeechVariable": [],
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
        "BizKnowledgeInfo": [
            {
                "knowledgeId": 400,
                "title": "FAQ 1",
                "kdType": 1,
                "intents": [{"intentId": 200}, {"intentId": 201}]
            }
        ]
    }
    p = tmp_path / "kb.json"
    p.write_text(_json.dumps(payload), encoding="utf-8")
    wf = parse_file(p)
    assert 400 in wf.knowledge_bases
    kb = wf.knowledge_bases[400]
    assert kb.knowledge_id == 400
    assert kb.title == "FAQ 1"
    assert kb.kd_type == 1
    assert kb.intents == (200, 201)

