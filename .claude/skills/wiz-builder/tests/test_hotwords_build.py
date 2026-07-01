"""Tests for apply_hotwords functionality in the builder."""

import json
from pathlib import Path

from wizbuilder.compile import compile_manifest

FIX = Path(__file__).resolve().parent / "fixtures"


def _build(tmp_path, manifest):
    out = tmp_path / "s.json"
    compile_manifest(FIX / manifest, out)
    return json.loads(out.read_text(encoding="utf-8"))


def test_manifest_hot_words_emits_global_row(tmp_path):
    doc = _build(tmp_path, "manifest_hotwords.yaml")
    rows = json.loads(doc["BizNodeHotWords"])
    glob = [r for r in rows if not (r.get("nodeId") or "")]
    assert len(glob) == 1
    assert set(glob[0]["hotWords"].split(",")) == {"indosat", "gopay", "gojek"}
    assert glob[0]["engineType"] == "3" and glob[0]["status"] == 2 and glob[0]["isDelete"] == 0


def test_no_hot_words_emits_no_rows(tmp_path):
    doc = _build(tmp_path, "manifest_minimal.yaml")
    rows = json.loads(doc.get("BizNodeHotWords", "[]"))
    assert rows == []
