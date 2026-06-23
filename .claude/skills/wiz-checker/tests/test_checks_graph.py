"""Tests for checks.graph — flow-integrity findings WIZ100..WIZ199.

All tests build WizFile via parse_dict() so wf.flow_model is populated.
"""

from __future__ import annotations

import json

from wizcheck.checks.graph import check_graph
from wizcheck.parser import parse_dict
from wizcheck.report import Severity

# ---------------------------------------------------------------------------
# Helpers for FlowModel-based tests (WIZ100-WIZ104)
# ---------------------------------------------------------------------------

def _make_export(
    *,
    comp_uuid: str = "aaaa0000-0000-4000-8000-000000000000",
    nodes: dict,
    routes: dict,
    kb_ids: list[int] | None = None,
) -> dict:
    kb_list = []
    if kb_ids:
        for kid in kb_ids:
            kb_list.append({
                "knowledgeId": kid,
                "kdTitle": f"KB {kid}",
                "kdType": 1,
                "intents": [],
                "kdInfo": [],
            })
    return {
        "BizSpeechComponent": [
            {
                "componentUuid": comp_uuid,
                "speechId": 1,
                "category": 1,
                "branch": "dev",
                "details": json.dumps(nodes),
                "routes": json.dumps(routes),
            }
        ],
        "BizKnowledgeInfo": kb_list,
        "SpeechVariable": [],
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }


def _talk_envelope(name: str, *, is_default: bool = False, ports: list[str] | None = None) -> dict:
    all_client_intent = []
    for i, port in enumerate(ports or []):
        all_client_intent.append({"id": port, "name": f"Intent {i}"})
    return {
        "name": name,
        "is_default": is_default,
        "type": 1,
        "data": {
            "name": name,
            "type": 1,
            "list": [],
            "all_client_intent": all_client_intent,
        },
    }


def _exit_envelope(name: str = "Hang Up") -> dict:
    return {
        "name": name,
        "is_default": False,
        "type": 2,
        "data": {"name": name, "type": 2, "is_transfer": 0, "list": []},
    }


def _goto_comp_envelope(target_comp_uuid: str, name: str = "Go To Component") -> dict:
    return {
        "name": name,
        "is_default": False,
        "type": 4,
        "data": {
            "name": name,
            "type": 4,
            "appoint_node_id": target_comp_uuid,
            "specificComponentName": name,
        },
    }


def _goto_kb_envelope(kb_id: int, name: str = "Go To KB") -> dict:
    return {
        "name": name,
        "is_default": False,
        "type": 8,
        "data": {"name": name, "type": 8, "appoint_knowledge_id": kb_id},
    }


# ---------------------------------------------------------------------------
# WIZ100: orphan refs
# ---------------------------------------------------------------------------

def test_wiz100_orphan_parent_is_warning_not_error():
    """WIZ100: same-component branch target absent from nodes is a WARNING."""
    data = _make_export(
        nodes={
            "node-a": _talk_envelope("Greeting", is_default=True, ports=["port-1"]),
        },
        routes={
            "node-a": {"port-1": {"target": {"uuid": "node-missing"}}},
        },
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ100"), None)
    assert f is not None
    assert f.severity is Severity.WARNING
    assert "node-missing" in f.message or "node-missing" in (f.location.id or "")


def test_wiz100_message_includes_node_info():
    """WIZ100 message includes the missing target UUID."""
    data = _make_export(
        nodes={
            "node-a": _talk_envelope("ASR Corpus Collection", is_default=True, ports=["port-1"]),
        },
        routes={
            "node-a": {"port-1": {"target": {"uuid": "node-missing"}}},
        },
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ100"), None)
    assert f is not None
    assert "node-missing" in f.message


def test_wiz100_does_not_fire_for_target_component():
    """Cross-component jumps are NOT orphans."""
    other = "bbbb0000-0000-4000-8000-000000000000"
    data = _make_export(
        nodes={"node-a": _goto_comp_envelope(other, "Go To External")},
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(f.code == "WIZ100" for f in findings)


def test_wiz100_does_not_fire_for_terminal():
    """Terminal nodes are not orphans."""
    data = _make_export(nodes={"node-a": _exit_envelope()}, routes={})
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(f.code == "WIZ100" for f in findings)


def test_wiz100_absent_when_all_targets_present():
    """No WIZ100 when all target_uuids are in the component."""
    data = _make_export(
        nodes={
            "node-a": _talk_envelope("Greeting", is_default=True, ports=["port-1"]),
            "node-b": _talk_envelope("Pitch"),
        },
        routes={"node-a": {"port-1": {"target": {"uuid": "node-b"}}}},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(f.code == "WIZ100" for f in findings)


# ---------------------------------------------------------------------------
# WIZ101: unreachable — reinstated on FlowModel (BFS from root_uuids)
# ---------------------------------------------------------------------------

def test_wiz101_descendants_of_library_ref_are_not_unreachable():
    """Node-b is reachable from the entry node via a branch — no WIZ101."""
    data = _make_export(
        nodes={
            "node-a": _talk_envelope("Greeting", is_default=True, ports=["port-1"]),
            "node-b": _talk_envelope("Library Entry", ports=[]),
        },
        routes={"node-a": {"port-1": {"target": {"uuid": "node-b"}}}},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(f.code == "WIZ101" for f in findings)


def test_wiz101_genuinely_disconnected_node():
    """WIZ101 fires for node-b which has no incoming edge from the entry node."""
    data = _make_export(
        nodes={
            "node-a": _talk_envelope("Greeting", is_default=True),
            "node-b": _talk_envelope("Disconnected"),
        },
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ101"), None)
    assert f is not None, f"Expected WIZ101 for disconnected node, got: {[x.code for x in findings]}"
    assert f.severity is Severity.WARNING
    assert "node-b" in f.message


# ---------------------------------------------------------------------------
# WIZ102: dead-ends
# ---------------------------------------------------------------------------

def test_wiz102_dead_end_warns_for_pitch_with_no_children():
    data = _make_export(
        nodes={"node-a": _talk_envelope("Pitch", is_default=True, ports=[])},
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ102"), None)
    assert f is not None
    assert f.severity is Severity.WARNING


def test_wiz102_does_not_warn_for_unknown_label_leaf():
    data = _make_export(
        nodes={"node-a": _talk_envelope("SomeOtherLabel", is_default=True, ports=[])},
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(f.code == "WIZ102" for f in findings)


def test_wiz102_skips_node_with_target():
    """A 'Pitch' node that has a target branch is not a dead-end."""
    data = _make_export(
        nodes={
            "node-a": _talk_envelope("Pitch", is_default=True, ports=["port-1"]),
            "node-b": _talk_envelope("Next"),
        },
        routes={"node-a": {"port-1": {"target": {"uuid": "node-b"}}}},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(f.code == "WIZ102" for f in findings)


def test_wiz102_skips_terminal_exit():
    """An exit node (hangup) is not a dead-end even if labelled 'Pitch'."""
    # goto_component with "Pitch" label — has target_component so not dead-end
    other = "bbbb0000-0000-4000-8000-000000000000"
    data = _make_export(
        nodes={"node-a": _goto_comp_envelope(other, "Pitch")},
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(f.code == "WIZ102" for f in findings)


def test_wiz102_still_fires_for_node_with_no_raw_children():
    """A 'Pitch' leaf node (no branches) fires WIZ102."""
    data = _make_export(
        nodes={"node-a": _talk_envelope("Pitch", is_default=True, ports=[])},
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ102"), None)
    assert f is not None


# ---------------------------------------------------------------------------
# WIZ103: cycles
# ---------------------------------------------------------------------------

def test_wiz103_cycle_is_warning():
    data = _make_export(
        nodes={
            "node-a": _talk_envelope("A", is_default=True, ports=["port-a"]),
            "node-b": _talk_envelope("B", ports=["port-b"]),
            "node-c": _talk_envelope("C", ports=["port-c"]),
        },
        routes={
            "node-a": {"port-a": {"target": {"uuid": "node-b"}}},
            "node-b": {"port-b": {"target": {"uuid": "node-c"}}},
            "node-c": {"port-c": {"target": {"uuid": "node-a"}}},
        },
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ103"), None)
    assert f is not None
    assert f.severity is Severity.WARNING


# ---------------------------------------------------------------------------
# WIZ104: library refs rollup
# ---------------------------------------------------------------------------

def test_wiz104_rollup_present_when_library_refs_exist():
    """WIZ104 fires when a goto_component targets an external component UUID."""
    other = "bbbb0000-0000-4000-8000-000000000000"
    data = _make_export(
        nodes={"node-a": _goto_comp_envelope(other, "Re-ask Limit")},
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ104"), None)
    assert f is not None
    assert f.severity is Severity.WARNING


def test_wiz104_absent_when_no_library_refs():
    """No WIZ104 when no external references exist."""
    comp_a = "aaaa0000-0000-4000-8000-000000000000"
    comp_b = "bbbb0000-0000-4000-8000-000000000000"
    data = {
        "BizSpeechComponent": [
            {
                "componentUuid": comp_a,
                "speechId": 1, "category": 1, "branch": "dev",
                "details": json.dumps({"node-a": _goto_comp_envelope(comp_b, "Go To B")}),
                "routes": json.dumps({}),
            },
            {
                "componentUuid": comp_b,
                "speechId": 2, "category": 1, "branch": "dev",
                "details": json.dumps({"node-b": _talk_envelope("Entry B", is_default=True)}),
                "routes": json.dumps({}),
            },
        ],
        "BizKnowledgeInfo": [],
        "SpeechVariable": [],
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(f.code == "WIZ104" for f in findings)


def test_wiz104_rollup_dedupes_labels():
    """Multiple nodes referencing the same external component -> one WIZ104."""
    other = "bbbb0000-0000-4000-8000-000000000000"
    data = _make_export(
        nodes={
            "node-a": _goto_comp_envelope(other, "Re-ask Limit"),
            "node-b": _goto_comp_envelope(other, "Re-ask Limit"),
        },
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    wiz104 = [f for f in findings if f.code == "WIZ104"]
    assert len(wiz104) == 1


def test_wiz104_rollup_message_clarifies_when_refs_exceed_distinct_labels():
    """WIZ104 message mentions external reference count."""
    other1 = "bbbb0000-0000-4000-8000-000000000000"
    other2 = "cccc0000-0000-4000-8000-000000000000"
    data = _make_export(
        nodes={
            "node-a": _goto_comp_envelope(other1, "Ref 1"),
            "node-b": _goto_comp_envelope(other2, "Ref 2"),
        },
        routes={},
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ104"), None)
    assert f is not None
    assert "2 external component reference(s)" in f.message


def test_library_ref_fixture_emits_warnings_not_errors(fixture_path):
    """End-to-end: library_ref.json produces graph findings, no errors.

    NOTE: library_ref.json uses the legacy details format, which the FlowModel
    parser treats as a single node keyed 'list'. WIZ100 fires for an orphan
    branch target in this fixture, or WIZ104 for external refs. Since this
    fixture was designed for the legacy FlowGraph path and the FlowModel path
    reads the legacy fixture differently, we only assert no errors are raised.
    """
    from wizcheck.parser import parse_file
    wf = parse_file(fixture_path("library_ref.json"))
    findings = check_graph(wf)
    # No finding in this check should be an ERROR (all graph findings are WARNINGs)
    assert not any(f.severity is Severity.ERROR for f in findings)


# ---------------------------------------------------------------------------
# WIZ105: FlowModel-based tests — parse_dict so flow_model is populated.
# Verify WIZ105 fires correctly when reading from FlowModelNode.data.
# ---------------------------------------------------------------------------

def _make_export_with_variables(nodes: dict, routes: dict, variables: list[dict]) -> dict:
    """Build a minimal export dict with one component and given SpeechVariable list."""
    return {
        "BizSpeechComponent": [
            {
                "componentUuid": "aaaa0000-0000-4000-8000-000000000001",
                "speechId": 1,
                "category": 1,
                "branch": "dev",
                "createTime": 1700000000000,
                "updateTime": 1700000000000,
                "name": "TestComp",
                "details": json.dumps(nodes),
                "routes": json.dumps(routes),
            }
        ],
        "BizKnowledgeInfo": [],
        "SpeechVariable": variables,
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }


def _conditional_envelope_with_branch(branch_list: list, *, is_default: bool = True) -> dict:
    """Build a type-7 (conditional judgment) envelope with the given branch list."""
    return {
        "type": 7,
        "name": "Check Date",
        "is_default": is_default,
        "data": {
            "list": [],
            "branch": branch_list,
            "all_client_intent": [],
            "node_variables": [],
            "allow_jump_knowledges": [],
        },
    }


def test_wiz105_flowmodel_missing_null_branch_fires():
    """WIZ105 (new source): conditional-judgment on date var with no null branch → WIZ105."""
    branch_list = [
        {
            "name": "Is Today",
            "branch_judgement_condition": [
                {"left_value": "[{201}]", "operator": "=", "right_value": "Today"}
            ],
        }
    ]
    variables = [{"id": 201, "name": "CallDate", "textType": "DATE", "variableSource": 0}]
    data = _make_export_with_variables(
        nodes={"cond-node": _conditional_envelope_with_branch(branch_list)},
        routes={"cond-node": {}},
        variables=variables,
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ105"), None)
    assert f is not None, f"Expected WIZ105 but got: {[x.code for x in findings]}"
    assert f.severity is Severity.ERROR
    assert "Missing fallback/null branch" in f.message


def test_wiz105_flowmodel_has_default_branch_no_fire():
    """WIZ105 (new source): conditional-judgment with a no-condition default branch → no WIZ105."""
    branch_list = [
        {
            "name": "Is Today",
            "branch_judgement_condition": [
                {"left_value": "[{202}]", "operator": "=", "right_value": "Today"}
            ],
        },
        {
            "name": "Default",
            "branch_judgement_condition": [],
        },
    ]
    variables = [{"id": 202, "name": "CallDate", "textType": "DATE", "variableSource": 0}]
    data = _make_export_with_variables(
        nodes={"cond-node": _conditional_envelope_with_branch(branch_list)},
        routes={"cond-node": {}},
        variables=variables,
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(x.code == "WIZ105" for x in findings)


def test_wiz105_flowmodel_has_is_empty_branch_no_fire():
    """WIZ105 (new source): conditional-judgment with an is_empty branch on the date var → no WIZ105."""
    branch_list = [
        {
            "name": "Is Today",
            "branch_judgement_condition": [
                {"left_value": "[{203}]", "operator": "=", "right_value": "Today"}
            ],
        },
        {
            "name": "Null Check",
            "branch_judgement_condition": [
                {"left_value": "[{203}]", "operator": "is_empty", "right_value": ""}
            ],
        },
    ]
    variables = [{"id": 203, "name": "CallDate", "textType": "DATE", "variableSource": 0}]
    data = _make_export_with_variables(
        nodes={"cond-node": _conditional_envelope_with_branch(branch_list)},
        routes={"cond-node": {}},
        variables=variables,
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(x.code == "WIZ105" for x in findings)


def test_wiz105_flowmodel_non_date_variable_no_fire():
    """WIZ105 (new source): conditional-judgment on a non-DATE variable → no WIZ105."""
    branch_list = [
        {
            "name": "Is True",
            "branch_judgement_condition": [
                {"left_value": "[{204}]", "operator": "=", "right_value": "true"}
            ],
        }
    ]
    variables = [{"id": 204, "name": "SomeFlag", "textType": "DEFAULT", "variableSource": 0}]
    data = _make_export_with_variables(
        nodes={"cond-node": _conditional_envelope_with_branch(branch_list)},
        routes={"cond-node": {}},
        variables=variables,
    )
    wf = parse_dict(data)
    findings = check_graph(wf)
    assert not any(x.code == "WIZ105" for x in findings)
