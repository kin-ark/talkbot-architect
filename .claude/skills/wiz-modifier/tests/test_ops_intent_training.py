"""Tests for intent training ops — set-intent-training."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SK / "wiz-builder" / "scripts"))
sys.path.insert(0, str(_SK / "wiz-modifier" / "scripts"))

from wizbuilder.compile import compile_manifest  # noqa: E402
from wizbuilder.ids import IdMinter  # noqa: E402
from wizmodifier import codec  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops.content import set_intent_training  # noqa: E402

_FIX = _SK / "wiz-builder" / "tests" / "fixtures"


def _bundle(tmp_path, manifest="manifest_with_kb.yaml"):
    out = tmp_path / "s.json"
    compile_manifest(_FIX / manifest, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    return InputBundle(data=data, speech_name="s.json")


def _minter(b=None):
    return IdMinter(manifest_hash="test-intent-training")


def test_set_intent_training_replaces(tmp_path):
    b = _bundle(tmp_path, "manifest_with_kb.yaml")  # has custom intent "AskPayment"
    set_intent_training(
        b,
        {
            "name": "AskPayment",
            "keywords": ["bayar", "tagihan"],
            "user_responses": ["saya mau bayar", "berapa tagihan"],
        },
        _minter(b),
    )
    si = codec.decode(b.data["SpeechIntent"])
    it = next(i for i in si if i["intentName"] == "AskPayment")
    assert "bayar" in it["keyWordInIntent"] and "saya mau bayar" in it["userResponseInIntent"]


def test_set_intent_training_omit_leaves_unchanged(tmp_path):
    b = _bundle(tmp_path, "manifest_with_kb.yaml")
    si0 = codec.decode(b.data["SpeechIntent"])
    kw0 = next(i for i in si0 if i["intentName"] == "AskPayment")["keyWordInIntent"]
    set_intent_training(
        b, {"name": "AskPayment", "user_responses": ["x"]}, _minter(b)
    )  # no keywords
    it = next(i for i in codec.decode(b.data["SpeechIntent"]) if i["intentName"] == "AskPayment")
    assert it["keyWordInIntent"] == kw0  # unchanged


def test_set_intent_training_unknown_raises(tmp_path):
    b = _bundle(tmp_path, "manifest_with_kb.yaml")
    with pytest.raises(ValueError):
        set_intent_training(b, {"name": "Nope", "keywords": ["a"]}, _minter(b))
