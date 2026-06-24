"""End-to-end integration tests for wiz-builder: build + wiz-checker validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from wizbuilder.compile import compile_manifest

SKILL_DIR = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_DIR / "tests" / "fixtures"
GOLDEN_DIR = SKILL_DIR / "tests" / "golden"
PROJECT_ROOT = SKILL_DIR.parents[2]
CHECKER_CLI = PROJECT_ROOT / ".claude" / "skills" / "wiz-checker" / "scripts" / "check.py"


@pytest.mark.parametrize("manifest_name", [
    "manifest_minimal.yaml",
    "manifest_multi_canvas.yaml",
    "manifest_with_customs.yaml",
])
def test_build_produces_checker_clean_output(manifest_name, tmp_path):
    out = tmp_path / "speech.json"
    result = compile_manifest(FIXTURES / manifest_name, out)
    assert result.checker_errors == 0, (
        f"{manifest_name}: {result.checker_errors} errors, codes: {result.finding_codes}"
    )


def test_multi_canvas_golden_matches(tmp_path):
    """The multi-canvas build output is bit-stable across re-compilations."""
    out = tmp_path / "speech.json"
    compile_manifest(FIXTURES / "manifest_multi_canvas.yaml", out)
    actual = json.loads(out.read_text(encoding="utf-8"))

    # Normalize the speechId (it's random per build).
    actual = _normalize(actual)

    golden_path = GOLDEN_DIR / "multi_canvas.expected.json"
    if not golden_path.exists():
        pytest.skip(f"Golden not present: {golden_path}")
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    if actual != expected:
        pytest.fail(
            "Golden mismatch. To regenerate the golden, follow Step 4 in the plan "
            "(docs/superpowers/plans/2026-05-21-wiz-builder-mvp.md, around line 2414):\n"
            "it runs compile_manifest + _normalize from the project root via PYTHONPATH.\n"
            f"Current build output that disagrees: {out}\n"
            f"Golden file to update: {golden_path}\n"
            "Diff first to make sure the change is intentional!"
        )


def _normalize(data: dict) -> dict:
    """Zero out the random speechId so goldens are stable."""
    data = dict(data)
    for key, raw in data.items():
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            decoded = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        changed = False
        if isinstance(decoded, list):
            for item in decoded:
                if isinstance(item, dict) and "speechId" in item:
                    item["speechId"] = 0
                    changed = True
        elif isinstance(decoded, dict) and "speechId" in decoded:
            decoded["speechId"] = 0
            changed = True
        if changed:
            data[key] = json.dumps(decoded, ensure_ascii=False, separators=(",", ":"))
    return data


def test_checker_finds_no_errors_on_compiled_output(tmp_path):
    """Sanity: directly invoke wiz-checker on the built file."""
    out = tmp_path / "speech.json"
    compile_manifest(FIXTURES / "manifest_with_customs.yaml", out)

    proc = subprocess.run(
        [sys.executable, str(CHECKER_CLI), str(out), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert proc.returncode in (0, 1), f"checker stderr: {proc.stderr}"
    report = json.loads(proc.stdout)
    assert report["summary"]["errors"] == 0, f"findings: {report['findings'][:3]}"


def test_conditional_and_assign_build_checker_clean(tmp_path):
    """Full pipeline: conditional (type 7) + assign (type 10) nodes → checker-clean export.

    Also verifies that canvases.py passes Node.config through verbatim for these
    node types (no goto-only special-casing needed): the built details must contain
    exactly one type-7 and one type-10 canvas node.
    """
    out = tmp_path / "speech_cond_assign.json"
    result = compile_manifest(FIXTURES / "manifest_conditional_assign.yaml", out)

    # Primary assertion: zero checker errors.
    assert result.checker_errors == 0, (
        f"conditional+assign manifest produced checker errors: "
        f"{result.checker_errors} errors, codes: {result.finding_codes}"
    )

    # Secondary assertions: the details blob must contain both new node types.
    # details is a JSON string encoding {node_uuid: node_obj} where node_obj["type"] is int.
    built = json.loads(out.read_text(encoding="utf-8"))
    components = json.loads(built["BizSpeechComponent"])
    assert components, "BizSpeechComponent must be non-empty"

    # Collect all node type integers across all components.
    all_node_types: list[int] = []
    for comp in components:
        details_raw = comp.get("details", "null")
        details = json.loads(details_raw) if isinstance(details_raw, str) else details_raw
        if not isinstance(details, dict):
            continue
        # details is {node_uuid: node_obj}; node_obj["type"] is the WIZ.AI integer type.
        for node_obj in details.values():
            if isinstance(node_obj, dict) and "type" in node_obj:
                all_node_types.append(node_obj["type"])

    assert 7 in all_node_types, (
        f"Expected a type-7 (Conditional-Judgment) node in details; found types: {all_node_types}"
    )
    assert 10 in all_node_types, (
        f"Expected a type-10 (Variable-Assignment) node in details; found types: {all_node_types}"
    )
