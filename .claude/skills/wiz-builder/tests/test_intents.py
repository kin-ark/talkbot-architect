"""Tests for wizbuilder.intents — apply_intents step."""

from __future__ import annotations

import json

from wizbuilder.ids import IdMinter, manifest_hash_of
from wizbuilder.intents import apply_intents
from wizbuilder.manifest import Canvas, CustomIntent, Manifest, Node


def _manifest(custom_intents: tuple[CustomIntent, ...]) -> Manifest:
    raw = "name: X\nbranch: dev\nlanguage: IDN\n"
    return Manifest(
        name="X",
        branch="dev",
        language="IDN",
        custom_variables=(),
        custom_intents=custom_intents,
        canvases=(Canvas(name="c", nodes=(Node(id="r", prompt="Greeting"),), edges=()),),
        raw_text=raw,
    )


def test_apply_intents_no_customs_keeps_defaults(template_dict):
    m = _manifest(())
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    assert len(intents) == 15
    names = {i["intentName"] for i in intents}
    assert "Unclassified" in names
    assert "Positive" in names
    assert "DNC" in names


def test_apply_intents_appends_custom_intent(template_dict):
    m = _manifest((CustomIntent(name="AskExtension", language="IDN"),))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    assert len(intents) == 16
    names = {i["intentName"] for i in intents}
    assert "AskExtension" in names


def test_custom_intent_has_correct_language(template_dict):
    m = _manifest((CustomIntent(name="AskExtension", language="IDN"),))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    custom = next(i for i in intents if i["intentName"] == "AskExtension")
    assert custom["language"] == "IDN"


def test_custom_intent_keywords_encoded_as_bracket_string(template_dict):
    """WIZ.AI exports encode keyWordInIntent as comma-separated bracket strings: '[a,b,c]'."""
    m = _manifest((
        CustomIntent(name="AskExtension", language="IDN", keywords=("bisa tunda", "extension")),
    ))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    custom = next(i for i in intents if i["intentName"] == "AskExtension")
    assert custom["keyWordInIntent"] == "[bisa tunda,extension]"


def test_custom_intent_user_responses_encoded_as_bracket_string(template_dict):
    m = _manifest((
        CustomIntent(
            name="AskExtension",
            language="IDN",
            user_responses=("bisa diundur?", "saya minta extension"),
        ),
    ))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    custom = next(i for i in intents if i["intentName"] == "AskExtension")
    assert custom["userResponseInIntent"] == "[bisa diundur?;saya minta extension]"


def test_custom_intent_empty_keywords_and_responses(template_dict):
    """Empty keyword/response lists serialise as '[]' for both fields.

    Separator is irrelevant when the iterable is empty.
    """
    m = _manifest((CustomIntent(name="X", language="IDN", keywords=(), user_responses=()),))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    custom = next(i for i in intents if i["intentName"] == "X")
    assert custom["keyWordInIntent"] == "[]"
    assert custom["userResponseInIntent"] == "[]"


def test_custom_intent_single_keyword(template_dict):
    """Single-element keyword list produces '[only]' (no trailing separator)."""
    m = _manifest((CustomIntent(name="X", language="IDN", keywords=("only",)),))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    custom = next(i for i in intents if i["intentName"] == "X")
    assert custom["keyWordInIntent"] == "[only]"


def test_custom_intent_with_both_keywords_and_user_responses(template_dict):
    """Both fields are populated independently with the correct separators."""
    m = _manifest((
        CustomIntent(
            name="Both",
            language="IDN",
            keywords=("kw1", "kw2"),
            user_responses=("ur1", "ur2"),
        ),
    ))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    custom = next(i for i in intents if i["intentName"] == "Both")
    assert custom["keyWordInIntent"] == "[kw1,kw2]"
    assert custom["userResponseInIntent"] == "[ur1;ur2]"


def test_custom_intent_deterministic_id(template_dict, template_path):
    m = _manifest((CustomIntent(name="A", language="IDN"),))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(template_dict, m, minter)
    intents = json.loads(template_dict["SpeechIntent"])
    custom = next(i for i in intents if i["intentName"] == "A")
    id1 = custom["intentId"]

    tpl2 = json.loads(template_path.read_text(encoding="utf-8"))
    minter2 = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_intents(tpl2, m, minter2)
    intents2 = json.loads(tpl2["SpeechIntent"])
    custom2 = next(i for i in intents2 if i["intentName"] == "A")
    assert id1 == custom2["intentId"]
