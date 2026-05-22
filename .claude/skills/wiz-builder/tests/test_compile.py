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
