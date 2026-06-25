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


def test_deploy_fixes_f1_f2_f3(tmp_path):
    """Validate F1 (var dedup + textType), F2 (canonical operators), F3 (variable_source).

    Manifest declares both a NEW custom var (PayStatus) and a BASELINE var (Gender).
    A conditional node branches on PayStatus using ops NotIn, Contains, and =.
    """
    out = tmp_path / "speech_deploy_fixes.json"
    result = compile_manifest(FIXTURES / "manifest_deploy_fixes.yaml", out)

    # Primary: zero checker errors.
    assert result.checker_errors == 0, (
        f"deploy-fixes manifest produced checker errors: "
        f"{result.checker_errors} errors, codes: {result.finding_codes}"
    )

    built = json.loads(out.read_text(encoding="utf-8"))

    # --- F1: SpeechVariable dedup + textType ---
    speech_vars = json.loads(built["SpeechVariable"])
    gender_entries = [v for v in speech_vars if v["name"] == "Gender"]
    assert len(gender_entries) == 1, (
        f"F1 dedup failed: expected exactly 1 'Gender' entry, found {len(gender_entries)}"
    )
    pay_entries = [v for v in speech_vars if v["name"] == "PayStatus"]
    assert len(pay_entries) == 1, (
        f"F1 dedup: expected exactly 1 'PayStatus' entry, found {len(pay_entries)}"
    )
    assert pay_entries[0]["textType"] == "DEFAULT", (
        f"F1 textType: expected 'DEFAULT' for PayStatus, got {pay_entries[0]['textType']!r}"
    )

    # --- F2 + F3: inspect the conditional node ---
    components = json.loads(built["BizSpeechComponent"])
    assert components, "BizSpeechComponent must be non-empty"

    cond_data: dict | None = None
    for comp in components:
        details = json.loads(comp.get("details", "null") or "null")
        if not isinstance(details, dict):
            continue
        for node_obj in details.values():
            if isinstance(node_obj, dict) and node_obj.get("type") == 7:
                cond_data = node_obj["data"]
                break
        if cond_data is not None:
            break

    assert cond_data is not None, "Expected a type-7 (Conditional-Judgment) node in built export"

    # F2: operator tokens must be canonical (NotIn→"Not in", Contains→"Contain", =→"=")
    branch_list = cond_data.get("branch", [])
    op_by_branch = {
        rule["name"]: rule["branch_judgement_condition"][0]["operator"]
        for rule in branch_list
        if rule.get("branch_judgement_condition")
    }
    assert op_by_branch.get("NotInGroup") == "Not in", (
        f"F2: NotIn must map to 'Not in', got {op_by_branch.get('NotInGroup')!r}"
    )
    assert op_by_branch.get("ContainsGroup") == "Contain", (
        f"F2: Contains must map to 'Contain', got {op_by_branch.get('ContainsGroup')!r}"
    )
    assert op_by_branch.get("ExactMatch") == "=", (
        f"F2: '=' must stay '=', got {op_by_branch.get('ExactMatch')!r}"
    )

    # F3: variable_source for PayStatus must be 0 (int) — custom variable.
    for rule in branch_list:
        for cond in rule.get("branch_judgement_condition", []):
            vsrc = cond.get("variable_source")
            assert vsrc == 0, (
                f"F3: branch '{rule['name']}' variable_source must be int 0, got {vsrc!r}"
            )
    for nv in cond_data.get("node_variables", []):
        vsrc = nv.get("variableSource")
        assert vsrc == 0, (
            f"F3: node_variables entry for '{nv.get('name')}' variableSource must be int 0, "
            f"got {vsrc!r}"
        )


def test_build_nested_component_checker_clean(tmp_path):
    """Full pipeline: nested (type 11) + exit_port (type 4) nodes across two canvases.

    Structural assertions:
    - child.parentUuid == parent.componentUuid  (two-way link)
    - nested node's data.subComponentUuid == child.componentUuid
    - nested node's canvas.ports.items UUIDs == set of child exit_port node UUIDs
    - parent routes from nested node are keyed by child exit_port UUIDs
    - checker_errors == 0
    """
    out = tmp_path / "speech_nested.json"
    result = compile_manifest(FIXTURES / "manifest_nested.yaml", out)

    assert result.checker_errors == 0, (
        f"nested manifest produced checker errors: "
        f"{result.checker_errors} errors, codes: {result.finding_codes}"
    )

    built = json.loads(out.read_text(encoding="utf-8"))
    bsc = json.loads(built["BizSpeechComponent"])

    parent = next(c for c in bsc if c["name"] == "Parent")
    child = next(c for c in bsc if c["name"] == "Child")

    # Two-way link: child.parentUuid == parent.componentUuid
    assert child["parentUuid"] == parent["componentUuid"], (
        f"child.parentUuid {child['parentUuid']!r} != parent.componentUuid "
        f"{parent['componentUuid']!r}"
    )

    pdet = json.loads(parent["details"])
    cdet = json.loads(child["details"])

    # nested node (type 11) in parent details
    nested_uuid = next((u for u, n in pdet.items() if n["type"] == 11), None)
    assert nested_uuid is not None, "Expected a type-11 (Nested Component) node in parent details"
    nested = pdet[nested_uuid]

    # subComponentUuid == child.componentUuid
    assert nested["data"]["subComponentUuid"] == child["componentUuid"], (
        f"nested.data.subComponentUuid {nested['data']['subComponentUuid']!r} "
        f"!= child.componentUuid {child['componentUuid']!r}"
    )

    # ports mirror child exits: port.uuid == a child exit_port node uuid
    child_exit_uuids = {u for u, n in cdet.items() if n["type"] == 4}
    port_uuids = {it["uuid"] for it in nested["canvas"]["ports"]["items"]}
    assert port_uuids == child_exit_uuids, (
        f"nested port UUIDs {port_uuids} do not match child exit_port UUIDs {child_exit_uuids}"
    )

    # parent routes from nested node keyed by child-exit-uuid
    proutes = json.loads(parent["routes"])
    assert set(proutes[nested_uuid].keys()) == child_exit_uuids, (
        f"parent routes[nested] keys {set(proutes[nested_uuid].keys())} "
        f"!= child exit_port UUIDs {child_exit_uuids}"
    )


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
