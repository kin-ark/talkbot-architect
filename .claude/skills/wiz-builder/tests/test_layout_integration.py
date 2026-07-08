"""Integration test for auto-layout on component build."""

from __future__ import annotations

import json

from wizbuilder.compile import compile_manifest


def _components(data):
    """Extract BizSpeechComponent list from export dict."""
    v = data.get("BizSpeechComponent")
    return json.loads(v) if isinstance(v, str) else (v or [])


def test_built_nodes_are_positioned(fixture_path, tmp_path):
    """Verify that all nodes in every component have positioned data.top/data.left."""
    out = tmp_path / "speech.json"
    compile_manifest(fixture_path("manifest_multi_canvas.yaml"), out)
    data = json.loads(out.read_text(encoding="utf-8"))

    comps = _components(data)
    assert comps, "No components in compiled output"

    for comp_idx, c in enumerate(comps):
        det = c.get("details")
        if not det or det in ("null", ""):
            continue
        tree = json.loads(det) if isinstance(det, str) else det
        positions = []
        for node_uuid, node in tree.items():
            d = node.get("data") or {}
            assert isinstance(
                d.get("top"), int
            ), f"Component {comp_idx}, node {node_uuid}: top must be an int, got {d.get('top')}"
            assert isinstance(
                d.get("left"), int
            ), f"Component {comp_idx}, node {node_uuid}: left must be an int, got {d.get('left')}"
            positions.append((d["top"], d["left"]))
        assert (
            len(positions) == len(set(positions))
        ), f"Component {comp_idx}: nodes overlap (duplicate positions: {positions})"
