"""Tests for wizbuilder.identity — apply_identity step."""

from __future__ import annotations

import json
from uuid import UUID

from wizbuilder.identity import apply_identity
from wizbuilder.ids import IdMinter, manifest_hash_of
from wizbuilder.manifest import Canvas, Manifest, Node


def _manifest(name="My Bot", branch="dev", language="IDN") -> Manifest:
    raw = f"name: {name}\nbranch: {branch}\nlanguage: {language}\n"
    return Manifest(
        name=name,
        branch=branch,
        language=language,
        custom_variables=(),
        custom_intents=(),
        canvases=(
            Canvas(name="c", nodes=(Node(id="r", label="Greeting", parent=None),)),
        ),
        raw_text=raw,
    )


def test_apply_identity_sets_speech_id(template_dict):
    m = _manifest()
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    result = apply_identity(template_dict, m, minter)

    bsc = json.loads(result["BizSpeechComponent"])
    speech_id = bsc[0]["speechId"]
    assert 10**15 <= speech_id < 10**16

    for key in (
        "BizSpeechComponent",
        "SpeechVariable",
        "SpeechIntent",
        "SentenceCutSpeech",
        "SpeechAudio",
    ):
        raw = result.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        for item in json.loads(raw):
            if "speechId" in item:
                assert item["speechId"] == speech_id, f"{key} item has stale speechId"


def test_apply_identity_sets_branch_on_components(template_dict):
    m = _manifest(branch="prod")
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    result = apply_identity(template_dict, m, minter)
    bsc = json.loads(result["BizSpeechComponent"])
    assert all(c["branch"] == "prod" for c in bsc)


def test_apply_identity_replaces_component_uuid_deterministically(template_dict, template_path):
    m = _manifest()
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    bsc_before = json.loads(template_dict["BizSpeechComponent"])
    old_uuid = bsc_before[0]["componentUuid"]
    result = apply_identity(template_dict, m, minter)
    bsc_after = json.loads(result["BizSpeechComponent"])
    new_uuid = bsc_after[0]["componentUuid"]
    assert new_uuid != old_uuid
    UUID(new_uuid)  # well-formed

    # Second run with a fresh template copy + fresh minter from the same manifest hash → same UUID
    tpl2 = json.loads(template_path.read_text(encoding="utf-8"))
    minter2 = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    result2 = apply_identity(tpl2, m, minter2)
    bsc2 = json.loads(result2["BizSpeechComponent"])
    assert bsc2[0]["componentUuid"] == new_uuid


def test_apply_identity_preserves_intent_language(template_dict):
    """Default intents are seeded in the template with language IDN. Apply doesn't override."""
    m = _manifest(language="ENG")
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    result = apply_identity(template_dict, m, minter)
    intents = json.loads(result["SpeechIntent"])
    # All 15 default intents in the template have language IDN; identity should not modify them.
    # The manifest's language is the bot's PRIMARY language but custom intents (added later)
    # get tagged with it. Default intents keep their IDN language.
    assert all(i.get("language") == "IDN" for i in intents)


def test_apply_identity_does_not_create_new_top_level_keys(template_dict):
    """apply_identity only mutates existing keys; doesn't add new ones."""
    m = _manifest()
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    keys_before = set(template_dict.keys())
    result = apply_identity(template_dict, m, minter)
    assert set(result.keys()) == keys_before


def test_apply_identity_returns_same_dict_object(template_dict):
    """In-place mutation is fine (it's a build-time step); but the result reference is identical."""
    m = _manifest()
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    result = apply_identity(template_dict, m, minter)
    assert result is template_dict
