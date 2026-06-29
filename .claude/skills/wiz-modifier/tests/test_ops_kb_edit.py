"""Tests for KB edit ops — rename, set intents."""

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
from wizmodifier.ops.kb_edit import rename_kb, set_kb_intents  # noqa: E402

_FIX = _SK / "wiz-builder" / "tests" / "fixtures"


def _bundle(tmp_path, manifest="manifest_with_kb.yaml"):
    out = tmp_path / "s.json"
    compile_manifest(_FIX / manifest, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    return InputBundle(data=data, speech_name="s.json")


def _minter():
    return IdMinter(manifest_hash="test-kb-edit")


def test_rename_kb(tmp_path):
    b = _bundle(tmp_path)
    rename_kb(b, {"name": "Payment FAQ", "new_name": "Payments"}, _minter())
    titles = [k["kdTitle"] for k in codec.decode(b.data["BizKnowledgeInfo"])]
    assert "Payments" in titles and "Payment FAQ" not in titles


def test_rename_kb_dedup_guard(tmp_path):
    b = _bundle(tmp_path)
    # rename to a name that already exists -> error. Use the baseline's existing KB title.
    existing = codec.decode(b.data["BizKnowledgeInfo"])[0]["kdTitle"]
    with pytest.raises(ValueError):
        rename_kb(b, {"name": "Payment FAQ", "new_name": existing}, _minter())


def test_set_kb_intents_resolves(tmp_path):
    b = _bundle(tmp_path)
    # 'AskPayment' is declared in manifest_with_kb.yaml
    set_kb_intents(b, {"name": "Payment FAQ", "intents": ["AskPayment"]}, _minter())
    kb = next(k for k in codec.decode(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Payment FAQ")
    intents = codec.decode(kb["intents"])
    assert [i["intentName"] for i in intents] == ["AskPayment"]


def test_set_kb_intents_unknown_raises(tmp_path):
    b = _bundle(tmp_path)
    with pytest.raises(ValueError):
        set_kb_intents(b, {"name": "Payment FAQ", "intents": ["NoSuchIntent"]}, _minter())
