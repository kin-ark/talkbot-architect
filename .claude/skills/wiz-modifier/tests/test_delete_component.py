"""Tests for the delete-component op — safe cascade delete, blocks if referenced.

Fixtures reuse existing builder-compiled manifests (manifest_goto.yaml,
manifest_nested.yaml, manifest_with_multiround_kb.yaml) plus the
hand-assembled multi-round mini-export pattern from test_append_goto_mr.py —
no hand-written raw export JSON.
"""

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
from wizmodifier.apply import run_mods  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops.structure import delete_component  # noqa: E402

_FIX = _SK / "wiz-builder" / "tests" / "fixtures"
_TEMPLATE = _SK / "wiz-builder" / "templates" / "empty_dialogue.json"


def _bundle(tmp_path, manifest: str) -> InputBundle:
    out = tmp_path / "s.json"
    compile_manifest(_FIX / manifest, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    return InputBundle(data=data, speech_name="s.json")


def _minter():
    return IdMinter(manifest_hash="test-delete-component")


def _comps(b: InputBundle) -> list[dict]:
    raw = b.data["BizSpeechComponent"]
    return json.loads(raw) if isinstance(raw, str) else raw


def _index_of(comps: list[dict], name: str) -> int:
    return next(i for i, c in enumerate(comps) if c.get("name") == name)


# ---------------------------------------------------------------------------
# unreferenced component: cascades cleanly
# ---------------------------------------------------------------------------


def test_delete_unreferenced_component_cascades(tmp_path):
    b = _bundle(tmp_path, "manifest_goto.yaml")
    comps = _comps(b)
    idx = _index_of(comps, "1. A Canvas")
    a_uuid = comps[idx]["componentUuid"]

    scs_before = codec.decode(b.data.get("SentenceCutSpeech", "[]"))
    assert any(r.get("componentUuid") == a_uuid for r in scs_before)

    result = delete_component(b, {"component": idx}, _minter())

    comps_out = _comps(b)
    assert len(comps_out) == 1
    assert comps_out[0]["name"] == "2. B Canvas"
    assert result["deleted"] == "1. A Canvas"
    assert result["removed_scs"] > 0

    scs_after = codec.decode(b.data.get("SentenceCutSpeech", "[]"))
    assert not any(r.get("componentUuid") == a_uuid for r in scs_after)


# ---------------------------------------------------------------------------
# referenced by goto (type 4): blocked
# ---------------------------------------------------------------------------


def test_delete_blocks_when_referenced_by_goto(tmp_path):
    b = _bundle(tmp_path, "manifest_goto.yaml")
    comps = _comps(b)
    idx = _index_of(comps, "2. B Canvas")

    with pytest.raises(ValueError, match="still referenced by"):
        delete_component(b, {"component": idx}, _minter())

    # No mutation on block.
    assert len(_comps(b)) == 2


# ---------------------------------------------------------------------------
# has child component: blocked
# ---------------------------------------------------------------------------


def test_delete_blocks_when_has_child_component(tmp_path):
    b = _bundle(tmp_path, "manifest_nested.yaml")
    comps = _comps(b)
    idx = _index_of(comps, "Parent")

    with pytest.raises(ValueError, match="has child components"):
        delete_component(b, {"component": idx}, _minter())

    assert len(_comps(b)) == 2


# ---------------------------------------------------------------------------
# referenced by nested (type 11): blocked
# ---------------------------------------------------------------------------


def test_delete_blocks_when_referenced_by_nested(tmp_path):
    b = _bundle(tmp_path, "manifest_nested.yaml")
    comps = _comps(b)
    idx = _index_of(comps, "Child")

    with pytest.raises(ValueError, match="still referenced by"):
        delete_component(b, {"component": idx}, _minter())

    assert len(_comps(b)) == 2


# ---------------------------------------------------------------------------
# referenced by a KB multi-round delegate: blocked
# ---------------------------------------------------------------------------


def test_delete_blocks_when_referenced_by_kb_multiround(tmp_path):
    b = _bundle(tmp_path, "manifest_with_multiround_kb.yaml")
    comps = _comps(b)
    idx = _index_of(comps, "Handler")

    with pytest.raises(ValueError, match="still referenced by"):
        delete_component(b, {"component": idx}, _minter())

    assert len(_comps(b)) == 2


# ---------------------------------------------------------------------------
# referenced by goto_mr (type 9): blocked
# ---------------------------------------------------------------------------


def _make_mr_export():
    """3-component export (A cat1, B cat2 w/ a goto_mr node -> C, C cat2),
    same construction as test_append_goto_mr.py."""
    data = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
    comps = json.loads(data["BizSpeechComponent"])
    comp_a = comps[0]
    comp_a["name"] = "1. A Canvas"
    comp_a["componentUuid"] = "uuid-a"
    comp_a["category"] = 1
    comp_b = dict(comp_a)
    comp_b["name"] = "2. B Canvas"
    comp_b["componentUuid"] = "uuid-b"
    comp_b["sortIndex"] = 2
    comp_b["details"] = "null"
    comp_b["category"] = 2
    comp_c = dict(comp_a)
    comp_c["name"] = "3. C Canvas"
    comp_c["componentUuid"] = "uuid-c"
    comp_c["sortIndex"] = 3
    comp_c["details"] = "null"
    comp_c["category"] = 2
    data["BizSpeechComponent"] = json.dumps([comp_a, comp_b, comp_c])

    b = InputBundle(data=data, speech_name="s.json")
    run_mods(
        b,
        [{"op": "append-node", "component": 1,
          "node": {"id": "jump", "type": "goto_mr", "config": {"target": "3. C Canvas"}}}],
        manifest_hash="t",
    )
    return b


def test_delete_blocks_when_referenced_by_goto_mr():
    b = _make_mr_export()
    comps = _comps(b)
    idx = _index_of(comps, "3. C Canvas")

    with pytest.raises(ValueError, match="still referenced by"):
        delete_component(b, {"component": idx}, _minter())

    assert len(_comps(b)) == 3
