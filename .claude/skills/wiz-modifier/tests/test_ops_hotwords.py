"""Tests for set-hotwords op — global and per-node BizNodeHotWords."""

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
from wizmodifier.ops.content import set_hotwords  # noqa: E402

_FIX = _SK / "wiz-builder" / "tests" / "fixtures"


def _bundle(tmp_path, manifest="manifest_minimal.yaml"):
    out = tmp_path / "s.json"
    compile_manifest(_FIX / manifest, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    return InputBundle(data=data, speech_name="s.json")


def _minter(b=None):
    return IdMinter(manifest_hash="test-hotwords")


def test_set_global_hotwords(tmp_path):
    b = _bundle(tmp_path, "manifest_minimal.yaml")
    set_hotwords(b, {"hot_words": ["indosat", "gopay"]}, _minter(b))
    rows = codec.decode(b.data["BizNodeHotWords"])
    glob = [r for r in rows if not (r.get("nodeId") or "")]
    assert len(glob) == 1 and set(glob[0]["hotWords"].split(",")) == {"indosat", "gopay"}


def test_set_global_replace_then_clear(tmp_path):
    b = _bundle(tmp_path, "manifest_minimal.yaml")
    m = _minter(b)
    set_hotwords(b, {"hot_words": ["a", "b"]}, m)
    set_hotwords(b, {"hot_words": ["c"]}, m)           # replace
    rows = codec.decode(b.data["BizNodeHotWords"])
    glob = [r for r in rows if not (r.get("nodeId") or "")]
    assert len(glob) == 1 and glob[0]["hotWords"] == "c"
    set_hotwords(b, {"hot_words": []}, m)               # clear -> drop row
    rows = codec.decode(b.data["BizNodeHotWords"])
    assert [r for r in rows if not (r.get("nodeId") or "")] == []


def test_set_per_node_hotwords(tmp_path):
    b = _bundle(tmp_path, "manifest_minimal.yaml")
    # find a real node uuid from the built doc
    comps = codec.decode(b.data["BizSpeechComponent"])
    det = json.loads(comps[0]["details"])
    node_uuid = next(iter(det))
    set_hotwords(b, {"node": node_uuid, "hot_words": ["x", "y"]}, _minter(b))
    rows = codec.decode(b.data["BizNodeHotWords"])
    mine = [r for r in rows if r.get("nodeId") == node_uuid]
    assert len(mine) == 1 and set(mine[0]["hotWords"].split(",")) == {"x", "y"}


def test_set_per_node_unknown_raises(tmp_path):
    b = _bundle(tmp_path, "manifest_minimal.yaml")
    with pytest.raises(ValueError):
        set_hotwords(b, {"node": "no-such-uuid", "hot_words": ["x"]}, _minter(b))
