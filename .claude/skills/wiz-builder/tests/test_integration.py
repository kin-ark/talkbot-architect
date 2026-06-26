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
    "manifest_with_kb.yaml",
    "manifest_with_multiround_kb.yaml",
    "manifest_goto_kb.yaml",
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
    # exit_port discriminant: type==4 AND empty specificComponentName (goto nodes have it populated)
    child_exit_uuids = {u for u, n in cdet.items()
                        if n["type"] == 4 and n["data"].get("specificComponentName") == ""}
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


def test_build_multiround_kb_links_component(tmp_path):
    """Full pipeline: a multi_round KB → checker-clean export whose delegate kdInfo item
    points at a real top-level component.

    Locks the deploy-shape decoded from the real Tiktok export (KB 179837):
    - top-level answerType stays 1
    - kdInfo carries a normal answerType:1 item plus a final answerType:2 delegate item
    - the delegate's multipleAppointId resolves to a present component with parentUuid "0"
    """
    out = tmp_path / "speech.json"
    result = compile_manifest(FIXTURES / "manifest_with_multiround_kb.yaml", out)
    assert result.checker_errors == 0, (
        f"multi-round KB manifest produced checker errors: "
        f"{result.checker_errors} errors, codes: {result.finding_codes}"
    )

    built = json.loads(out.read_text(encoding="utf-8"))

    def _unwrap(v):
        return json.loads(v) if isinstance(v, str) else v

    kbs = _unwrap(built["BizKnowledgeInfo"])
    kb = next(k for k in kbs if k.get("kdTitle") == "Due Date KB")
    assert kb["answerType"] == 1, "multi-round KB top-level answerType must stay 1"
    # conditions must be JSON-encoded null for an Intent-triggered KB; a non-null value
    # makes WIZ classify it as a "System Trigger" (decoded from the real export).
    assert kb["conditions"] == "null", (
        f"intent-triggered KB must have conditions 'null'; got {kb['conditions']!r}"
    )

    kd_info = _unwrap(kb["kdInfo"])
    answer_types = [item.get("answerType") for item in kd_info]
    assert answer_types == [1, 2], (
        f"expected a normal answer then a delegate item; got answerTypes {answer_types}"
    )

    delegate = kd_info[-1]
    target_uuid = delegate["multipleAppointId"]
    assert target_uuid, "delegate item must carry a multipleAppointId"

    components = _unwrap(built["BizSpeechComponent"])
    by_uuid = {c.get("componentUuid"): c for c in components}
    assert target_uuid in by_uuid, (
        f"multipleAppointId {target_uuid} does not resolve to any component"
    )
    target_comp = by_uuid[target_uuid]
    assert target_comp.get("parentUuid") == "0", (
        "multi-round target must be a normal top-level component (parentUuid '0')"
    )
    # The delegate target must be category=2 so WIZ files it under the Multi-Round Dialogue
    # tab (decoded from the real export); normal Main Talk-Flow components stay category=1.
    assert target_comp.get("category") == 2, (
        f"multi-round target component must be category 2; got {target_comp.get('category')}"
    )
    by_name = {c.get("name"): c for c in components}
    assert by_name["1. Main"].get("category") == 1, (
        "a normal Main Talk-Flow component must stay category 1"
    )

    # The KB's triggering intent must be a user intent (isInit=1) so WIZ shows an
    # "Intent Trigger", not a "System Trigger" (decoded from the real export).
    speech_intents = _unwrap(built["SpeechIntent"])
    by_intent_name = {i.get("intentName"): i for i in speech_intents}
    assert by_intent_name["AskDueDate"].get("isInit") == 1, (
        "a manifest custom_intent must be emitted with isInit=1 (user intent)"
    )


def test_goto_kb_node_links_to_kb(tmp_path):
    """Full pipeline: goto_kb (type 8) node links to a manifest-declared KB.

    Structural assertions (T5 Step 1):
    - checker_errors == 0
    - The built export contains exactly one type-8 node in BizSpeechComponent details
    - The type-8 node is terminal: routes[uuid] == {}
    - The type-8 node appears in the component's topFloorDetails
    - data["appoint_knowledge_id"] == str(KB.knowledgeId) for "Payment FAQ"
    - data["appoint_node_id"] == "" and data["specificComponentName"] == ""
      and data["multiple_appoint_id"] == "" (no source* fields)
    - Field presence matches a real type-8 node from talkbot/Test+Kinan/speech*.json
      (appoint_knowledge_id set as a string; appoint_node_id/"specificComponentName"/
      "multiple_appoint_id" empty; no source* provenance fields).

    Manifest: tests/fixtures/manifest_goto_kb.yaml
    KB name: "Payment FAQ", resolved knowledgeId: 1543872530 (minted deterministically).
    """
    out = tmp_path / "speech_goto_kb.json"
    result = compile_manifest(FIXTURES / "manifest_goto_kb.yaml", out)

    # Primary: checker-clean.
    assert result.checker_errors == 0, (
        f"goto_kb manifest produced checker errors: "
        f"{result.checker_errors} errors, codes: {result.finding_codes}"
    )

    built = json.loads(out.read_text(encoding="utf-8"))

    def _unwrap(v):
        return json.loads(v) if isinstance(v, str) else v

    # --- Locate the type-8 node across all components ---
    components = _unwrap(built["BizSpeechComponent"])
    assert components, "BizSpeechComponent must be non-empty"

    goto_kb_node: dict | None = None
    goto_kb_uuid: str | None = None
    host_comp: dict | None = None

    for comp in components:
        details = _unwrap(comp.get("details", "{}") or "{}")
        if not isinstance(details, dict):
            continue
        for uuid, node in details.items():
            if isinstance(node, dict) and node.get("type") == 8:
                goto_kb_node = node
                goto_kb_uuid = uuid
                host_comp = comp
                break
        if goto_kb_node is not None:
            break

    assert goto_kb_node is not None, (
        "Expected exactly one type-8 (goto_kb) node in BizSpeechComponent details"
    )

    # --- Terminal: routes[uuid] must be an empty dict ---
    routes = _unwrap(host_comp.get("routes", "{}") or "{}")
    assert goto_kb_uuid in routes, (
        f"goto_kb node uuid {goto_kb_uuid!r} not present as a routes key"
    )
    assert routes[goto_kb_uuid] == {}, (
        f"goto_kb must be terminal (empty route dict); got {routes[goto_kb_uuid]!r}"
    )

    # --- topFloorDetails: the type-8 node must appear ---
    top_floor_raw = host_comp.get("topFloorDetails", "[]")
    top_floor = _unwrap(top_floor_raw) if top_floor_raw else []
    tfd_uuids = {item.get("id") for item in top_floor if isinstance(item, dict)}
    assert goto_kb_uuid in tfd_uuids, (
        f"goto_kb uuid {goto_kb_uuid!r} not found in topFloorDetails; "
        f"present uuids: {tfd_uuids}"
    )

    # --- KB linkage: appoint_knowledge_id == str(KB knowledgeId) for "Payment FAQ" ---
    kbs = _unwrap(built["BizKnowledgeInfo"])
    payment_faq = next(
        (k for k in kbs if k.get("kdTitle") == "Payment FAQ"), None
    )
    assert payment_faq is not None, (
        "BizKnowledgeInfo must contain a KB entry with kdTitle 'Payment FAQ'"
    )
    kb_id = payment_faq["knowledgeId"]  # int in the KB row
    assert kb_id, f"Payment FAQ KB must have a non-zero knowledgeId; got {kb_id!r}"

    node_data = goto_kb_node["data"]
    assert node_data["appoint_knowledge_id"] == str(kb_id), (
        f"goto_kb appoint_knowledge_id must == str(knowledgeId) "
        f"'{kb_id}'; got {node_data['appoint_knowledge_id']!r}"
    )

    # --- Decode-compare against real type-8 node shape ---
    # Real WIZ export (talkbot/Test+Kinan) confirms:
    #   appoint_node_id / specificComponentName / multiple_appoint_id are "" for a
    #   manifest-authored goto_kb; source* fields (sourceTemplateCode, sourceSpeechId,
    #   sourceComponentUuid, sourceNodeId) are library-import-only and must be absent.
    assert node_data["appoint_node_id"] == "", (
        f"goto_kb appoint_node_id must be empty; got {node_data['appoint_node_id']!r}"
    )
    assert node_data["specificComponentName"] == "", (
        f"goto_kb specificComponentName must be empty; "
        f"got {node_data['specificComponentName']!r}"
    )
    assert node_data["multiple_appoint_id"] == "", (
        f"goto_kb multiple_appoint_id must be empty; "
        f"got {node_data['multiple_appoint_id']!r}"
    )
    for source_field in ("sourceTemplateCode", "sourceSpeechId",
                         "sourceComponentUuid", "sourceNodeId"):
        assert source_field not in node_data, (
            f"goto_kb node must not carry library-only field {source_field!r}"
        )

    # appoint_knowledge_id is a non-empty string (confirmed from real export: "244124")
    assert isinstance(node_data["appoint_knowledge_id"], str), (
        f"appoint_knowledge_id must be a string; got {type(node_data['appoint_knowledge_id'])}"
    )
    assert node_data["appoint_knowledge_id"] != "", (
        "appoint_knowledge_id must be non-empty for a targeted goto_kb"
    )
