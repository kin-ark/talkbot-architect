"""Tests for the in-memory IR types in wizcheck.ir."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest
from wizcheck.ir import (
    Intent,
    Utterance,
    Variable,
    WizFile,
)

UUID_A = UUID("00000000-0000-4000-8000-000000000001")
UUID_B = UUID("00000000-0000-4000-8000-000000000002")


def test_variable_is_frozen_and_has_raw():
    v = Variable(
        id=1, name="Phone", text_type="PHONE",
        raw={"id": 1, "name": "Phone"}, variable_source=1,
    )
    assert v.id == 1
    assert v.name == "Phone"
    assert v.text_type == "PHONE"
    assert v.raw["name"] == "Phone"
    with pytest.raises(FrozenInstanceError):
        v.id = 2  # frozen dataclass must not allow mutation


def test_intent_carries_keywords_and_responses():
    i = Intent(
        intent_id=460827,
        name="Negative",
        language="IDN",
        keywords=("tidak", "nggak"),
        user_responses=("tidak mau",),
        raw={"intentId": 460827, "intentName": "Negative"},
    )
    assert i.name == "Negative"
    assert "tidak" in i.keywords


def test_utterance_referenced_vars_is_tuple():
    u = Utterance(
        id=UUID_A,
        component_uuid=UUID_B,
        text="Halo {Name}, selamat datang.",
        referenced_vars=("Name",),
        raw={"id": str(UUID_A)},
    )
    assert u.referenced_vars == ("Name",)


def test_wizfile_holds_all_collections():
    wf = WizFile(
        components={},
        variables={},
        intents={},
        utterances=(),
        audios={}, knowledge_bases={},
        raw={},
    )
    assert wf.components == {}
    assert wf.utterances == ()
