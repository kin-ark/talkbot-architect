"""Tests for wizbuilder.compile — end-to-end pipeline orchestration."""

from __future__ import annotations

import json

import pytest
from wizbuilder.compile import CompileError, CompileResult, compile_manifest


def test_compile_minimal_produces_valid_json(fixture_path, tmp_path):
    out = tmp_path / "speech.json"
    result = compile_manifest(fixture_path("manifest_minimal.yaml"), out)
    assert isinstance(result, CompileResult)
    assert result.output_path == out
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "BizSpeechComponent" in data


def test_compile_minimal_passes_checker(fixture_path, tmp_path):
    out = tmp_path / "speech.json"
    result = compile_manifest(fixture_path("manifest_minimal.yaml"), out)
    assert result.checker_errors == 0
    # Empty manifest minimal — likely has WIZ006 + WIZ301 satisfied (Unclassified present from defaults).  # noqa: E501
    # We accept warnings; errors must be 0.


def test_compile_multi_canvas_produces_two_components(fixture_path, tmp_path):
    out = tmp_path / "speech.json"
    compile_manifest(fixture_path("manifest_multi_canvas.yaml"), out)
    data = json.loads(out.read_text(encoding="utf-8"))
    bsc = json.loads(data["BizSpeechComponent"])
    assert len(bsc) == 2


def test_compile_invalid_manifest_raises(fixture_path, tmp_path):
    from wizbuilder.manifest import ManifestError
    out = tmp_path / "speech.json"
    with pytest.raises(ManifestError):
        compile_manifest(fixture_path("manifest_invalid_cross_canvas.yaml"), out)
    assert not out.exists()  # no partial output on failure


def test_compile_unlinks_partial_output_on_checker_rejection(fixture_path, tmp_path, monkeypatch):
    """If wiz-checker reports errors > 0, the partial speech.json must be deleted."""
    from wizbuilder import compile as compile_module

    def fake_run_checker(output_path):
        return compile_module.CompileResult(
            output_path=output_path,
            checker_errors=2,
            checker_warnings=0,
            finding_codes={"WIZ001": 1, "WIZ002": 1},
        )

    monkeypatch.setattr(compile_module, "_run_checker", fake_run_checker)

    out = tmp_path / "speech.json"
    with pytest.raises(CompileError):
        compile_module.compile_manifest(fixture_path("manifest_minimal.yaml"), out)
    assert not out.exists()


def test_compile_output_is_single_line_minified(fixture_path, tmp_path):
    """Builder output must be single-line minified (matching real WIZ exports)."""
    out = tmp_path / "speech.json"
    compile_manifest(fixture_path("manifest_minimal.yaml"), out)
    text = out.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) == 1, f"Expected single-line output, got {len(lines)} lines"
    # No spaces after colons at the top level
    assert '": "' not in text, "Found spaces after colons in top-level JSON"


def test_compile_is_idempotent_for_uuids(fixture_path, tmp_path):
    """Same manifest text → same UUIDs in the output."""
    out1 = tmp_path / "speech1.json"
    out2 = tmp_path / "speech2.json"
    compile_manifest(fixture_path("manifest_multi_canvas.yaml"), out1)
    compile_manifest(fixture_path("manifest_multi_canvas.yaml"), out2)
    d1 = json.loads(out1.read_text(encoding="utf-8"))
    d2 = json.loads(out2.read_text(encoding="utf-8"))
    bsc1 = json.loads(d1["BizSpeechComponent"])
    bsc2 = json.loads(d2["BizSpeechComponent"])
    uuids1 = sorted(c["componentUuid"] for c in bsc1)
    uuids2 = sorted(c["componentUuid"] for c in bsc2)
    assert uuids1 == uuids2


def test_builder_output_has_real_node_shape(fixture_path, tmp_path):
    """Compiled output must use the real node shape (not the old skeletal label/parentId shape).

    Concretely:
    - details is a dict keyed by node_uuid (not envelope_uuid)
    - each value has 'canvas', 'data', 'name', 'type', 'is_default', 'data_extra'
    - routes is a dict (not the string "[]")
    - inboundPorts is a non-empty JSON list (at least one entry node per canvas)
    - SentenceCutSpeech is a JSON list with rows (one per node)
    """
    out = tmp_path / "speech.json"
    compile_manifest(fixture_path("manifest_multi_canvas.yaml"), out)
    data = json.loads(out.read_text(encoding="utf-8"))

    bsc = json.loads(data["BizSpeechComponent"])
    assert len(bsc) == 2

    for comp in bsc:
        # details must be a dict keyed by node uuids
        details = json.loads(comp["details"])
        assert isinstance(details, dict), "details must be a dict"
        assert len(details) > 0, "details must be non-empty"

        for node_uuid, node_obj in details.items():
            assert "canvas" in node_obj, f"node {node_uuid} missing 'canvas'"
            assert "data" in node_obj, f"node {node_uuid} missing 'data'"
            assert "name" in node_obj, f"node {node_uuid} missing 'name'"
            assert node_obj["name"] == "Talk Node"
            assert "type" in node_obj
            assert "is_default" in node_obj
            assert "data_extra" in node_obj

        # routes must be a dict (keyed by node_uuid)
        routes = json.loads(comp["routes"])
        assert isinstance(routes, dict), "routes must be a dict"

        # inboundPorts must be a non-empty list with at least one entry node
        inbound = json.loads(comp["inboundPorts"])
        assert isinstance(inbound, list), "inboundPorts must be a list"
        assert len(inbound) > 0, "inboundPorts must have at least one entry"
        for port in inbound:
            assert "uuid" in port
            assert "name" in port
            assert port["is_default"] is True

    # SentenceCutSpeech must have one row per node across all canvases
    scs = json.loads(data["SentenceCutSpeech"])
    assert isinstance(scs, list)
    # multi_canvas manifest has 3 nodes total (2 in Greeting, 1 in Closing)
    assert len(scs) == 3, f"expected 3 SentenceCutSpeech rows, got {len(scs)}"
    for row in scs:
        assert "sentenceText" in row
        assert "componentUuid" in row
        assert "speechId" in row
