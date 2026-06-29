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
from wizmodifier.ops.kb_edit import (  # noqa: E402
    rename_kb,
    set_kb_intents,
    add_kb_answer,
    edit_kb_answer,
    remove_kb_answer,
)

_FIX = _SK / "wiz-builder" / "tests" / "fixtures"


def _bundle(tmp_path, manifest="manifest_with_kb.yaml"):
    out = tmp_path / "s.json"
    compile_manifest(_FIX / manifest, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    return InputBundle(data=data, speech_name="s.json")


def _minter(b=None):
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


def _editor_value(text):
    return {
        "xml": f'<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">{text}</speak>',
        "html": f"<p>{text}</p>",
        "text": text,
    }


def test_add_kb_answer_adds_item_and_sck(tmp_path):
    b = _bundle(tmp_path)
    add_kb_answer(b, {"name": "Payment FAQ", "text": "Brand new answer"}, _minter(b))
    kb = next(k for k in codec.decode(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Payment FAQ")
    items = codec.decode(kb["kdInfo"])
    assert any(it.get("answer") == "Brand new answer" for it in items if it.get("answerType") == 1)
    sck = [r for r in codec.decode(b.data["SentenceCutKnowledge"])
           if r["knowledgeId"] == kb["knowledgeId"] and r["sentenceText"] == "Brand new answer"]
    assert len(sck) == 1


def test_edit_kb_answer_syncs_and_resets_audio(tmp_path):
    b = _bundle(tmp_path)
    kb0 = next(k for k in codec.decode(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Payment FAQ")
    old_text = codec.decode(kb0["kdInfo"])[0]["answer"]
    # Simulate a recorded export: give the matching SCK row a non-empty audio url.
    sck = codec.decode(b.data["SentenceCutKnowledge"])
    item0_id = codec.decode(kb0["kdInfo"])[0]["id"]
    for r in sck:
        if r["id"] == item0_id:
            r["sentenceTextUrl"] = "https://audio/old.wav"
    b.data["SentenceCutKnowledge"] = codec.encode(sck)

    edit_kb_answer(b, {"name": "Payment FAQ", "old_text": old_text, "new_text": "Updated!"},
                   _minter(b))

    kb = next(k for k in codec.decode(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Payment FAQ")
    item = codec.decode(kb["kdInfo"])[0]
    assert item["answer"] == "Updated!" and item["editorValue"] == _editor_value("Updated!")
    row = next(r for r in codec.decode(b.data["SentenceCutKnowledge"]) if r["id"] == item0_id)
    assert row["sentenceText"] == "Updated!" and row["sentenceTextUrl"] == ""   # audio reset


def test_remove_kb_answer_drops_item_and_sck(tmp_path):
    b = _bundle(tmp_path)
    kb0 = next(k for k in codec.decode(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Payment FAQ")
    items0 = [it for it in codec.decode(kb0["kdInfo"]) if it.get("answerType") == 1]
    # ensure >1 answer so removal is allowed; add one first if the fixture has only one
    if len(items0) < 2:
        add_kb_answer(b, {"name": "Payment FAQ", "text": "Second"}, _minter(b))
    target_text = "Second" if len(items0) < 2 else items0[0]["answer"]
    remove_kb_answer(b, {"name": "Payment FAQ", "text": target_text}, _minter(b))
    kb = next(k for k in codec.decode(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Payment FAQ")
    items = [it for it in codec.decode(kb["kdInfo"]) if it.get("answerType") == 1]
    assert all(it["answer"] != target_text for it in items)


def test_remove_last_answer_raises(tmp_path):
    b = _bundle(tmp_path)
    kb0 = next(k for k in codec.decode(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Payment FAQ")
    answers = [it for it in codec.decode(kb0["kdInfo"]) if it.get("answerType") == 1]
    # remove down to one, then the last removal must raise
    for it in answers[1:]:
        remove_kb_answer(b, {"name": "Payment FAQ", "text": it["answer"]}, _minter(b))
    last = [it for it in codec.decode(
        next(k for k in codec.decode(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Payment FAQ")["kdInfo"])
        if it.get("answerType") == 1][0]
    with pytest.raises(ValueError):
        remove_kb_answer(b, {"name": "Payment FAQ", "text": last["answer"]}, _minter(b))
