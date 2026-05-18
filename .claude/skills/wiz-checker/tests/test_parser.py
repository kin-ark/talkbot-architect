"""Tests for wizcheck.parser."""

from __future__ import annotations

from uuid import UUID

import pytest
from wizcheck.ir import WizFile
from wizcheck.parser import parse_file


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
