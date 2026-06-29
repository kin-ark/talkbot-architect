"""Tests for KbEditor — KB table decode/find/flush."""

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
from wizmodifier.kbeditor import KbEditor  # noqa: E402

_FIX = _SK / "wiz-builder" / "tests" / "fixtures"


def _bundle(tmp_path, manifest="manifest_with_kb.yaml"):
    out = tmp_path / "s.json"
    compile_manifest(_FIX / manifest, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    return InputBundle(data=data, speech_name="s.json")


def _minter():
    return IdMinter(manifest_hash="test-kbeditor")


def test_kbeditor_roundtrip_is_stable(tmp_path):
    b = _bundle(tmp_path)
    before = b.data["BizKnowledgeInfo"]
    ed = KbEditor(b, _minter())
    ed.flush()
    # decode-encode round-trip must be value-stable (order + content preserved)
    assert codec.decode(b.data["BizKnowledgeInfo"]) == codec.decode(before)


def test_kbeditor_find_and_answers(tmp_path):
    b = _bundle(tmp_path)
    ed = KbEditor(b, _minter())
    # KB name from manifest_with_kb.yaml: "Payment FAQ"
    kb = ed.find_kb("Payment FAQ")
    items = ed.kd_items(kb)
    answers = ed.answer_items(items)
    assert len(answers) >= 1
    assert ed.sck_rows_for(kb["knowledgeId"])  # SCK rows exist for the answers


def test_kbeditor_find_missing_raises(tmp_path):
    b = _bundle(tmp_path)
    ed = KbEditor(b, _minter())
    with pytest.raises(ValueError):
        ed.find_kb("Nope")


def test_kbeditor_warn_appends_to_bundle_warnings(tmp_path):
    b = _bundle(tmp_path)
    ed = KbEditor(b, _minter())
    ed.warn("test warning")
    assert "test warning" in b.warnings


def test_kbeditor_set_kd_items_roundtrip(tmp_path):
    b = _bundle(tmp_path)
    ed = KbEditor(b, _minter())
    kb = ed.find_kb("Payment FAQ")
    items = ed.kd_items(kb)
    # set items back; flush; re-decode — should be identical
    ed.set_kd_items(kb, items)
    ed.flush()
    kb2 = ed.find_kb("Payment FAQ")
    assert ed.kd_items(kb2) == items


def test_kbeditor_sck_rows_for_returns_correct_rows(tmp_path):
    b = _bundle(tmp_path)
    ed = KbEditor(b, _minter())
    kb = ed.find_kb("Payment FAQ")
    rows = ed.sck_rows_for(kb["knowledgeId"])
    # all returned rows must have the matching knowledgeId
    for r in rows:
        assert r["knowledgeId"] == kb["knowledgeId"]


def test_kbeditor_bsc_loaded_lazily(tmp_path):
    b = _bundle(tmp_path)
    ed = KbEditor(b, _minter())
    # bsc should not have been loaded yet
    assert ed._bsc is None
    bsc = ed.bsc()
    assert isinstance(bsc, list)
    # second call returns same object (cached)
    assert ed.bsc() is bsc


def test_kbeditor_bsc_dirty_flag(tmp_path):
    b = _bundle(tmp_path)
    ed = KbEditor(b, _minter())
    ed.bsc()  # load
    before_bsc = b.data.get("BizSpeechComponent")
    # without marking dirty, flush should NOT re-encode BizSpeechComponent
    ed.flush()
    # With no dirty flag, the original BSC string should remain unchanged
    assert b.data.get("BizSpeechComponent") == before_bsc

    # Now mark dirty — flush should re-encode the in-memory bsc value (not just be non-None)
    ed.mark_bsc_dirty()
    ed.flush()
    assert codec.decode(b.data["BizSpeechComponent"]) == ed._bsc


def test_goto_kb_refs_finds_referencing_node(tmp_path):
    # manifest_goto_kb.yaml builds a KB + a goto_kb (type-8) node referencing it.
    b = _bundle(tmp_path, "manifest_goto_kb.yaml")
    ed = KbEditor(b, _minter())
    # find the user-created KB and confirm a goto_kb node references its id
    user_kb = next(k for k in ed.bk if k.get("isInit") == 0)
    refs = ed.goto_kb_refs(user_kb["knowledgeId"])
    assert refs, "expected a goto_kb node referencing the KB"
    # a knowledgeId that no node targets returns no refs
    assert ed.goto_kb_refs(99999999) == []


def test_goto_kb_refs_tolerates_null_details(tmp_path):
    b = _bundle(tmp_path)
    ed = KbEditor(b, _minter())
    # inject a component whose details is the literal "null" string — must not crash
    ed.bsc().append({"componentUuid": "x", "name": "empty", "details": "null"})
    assert ed.goto_kb_refs(12345) == []
