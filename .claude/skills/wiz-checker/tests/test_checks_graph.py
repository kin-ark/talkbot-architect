"""Tests for checks.graph — flow-integrity findings WIZ100..WIZ199."""

from __future__ import annotations

from uuid import UUID

from wizcheck.checks.graph import check_graph
from wizcheck.ir import (
    Component,
    ComponentDetails,
    FlowGraph,
    FlowNode,
    WizFile,
)
from wizcheck.report import Severity


def _node(uid, parent=None, label="Other") -> FlowNode:
    return FlowNode(uuid=uid, parent_uuid=parent, label=label, sort_index=0, raw={})


def _wf_from_nodes(nodes: list[FlowNode]) -> WizFile:
    by_uuid = {n.uuid: n for n in nodes}
    roots = tuple(n.uuid for n in nodes if n.parent_uuid is None)
    comp = Component(
        uuid=UUID(int=1),
        speech_id=1,
        category=1,
        branch="dev",
        details=ComponentDetails(flow_nodes=by_uuid, root_uuids=roots),
        raw={},
    )
    g = FlowGraph()
    for n in nodes:
        g.add_node(n.uuid)
    for n in nodes:
        if n.parent_uuid is not None:
            g.add_edge(n.parent_uuid, n.uuid)
    return WizFile(
        raw={},
        components={comp.uuid: comp},
        variables={},
        intents={},
        utterances=(),
        audios={},
        flow=g,
    )


def test_wiz100_orphan_reference_is_error():
    a, missing = UUID(int=10), UUID(int=11)
    n_a = _node(a)
    n_orphan_ref = _node(UUID(int=12), parent=missing)  # claims `missing` as parent
    wf = _wf_from_nodes([n_a, n_orphan_ref])
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ100"), None)
    assert f is not None
    assert f.severity is Severity.ERROR
    assert str(missing) in f.message or str(missing) in (f.location.id or "")


def test_wiz101_unreachable_node_is_warning():
    # A node whose parent is itself orphaned is unreachable from any valid root.
    a = UUID(int=20)
    orphan_parent = UUID(int=21)
    child = UUID(int=22)
    n_a = _node(a)
    n_child = _node(child, parent=orphan_parent)
    wf = _wf_from_nodes([n_a, n_child])
    findings = check_graph(wf)
    codes = [f.code for f in findings]
    assert "WIZ101" in codes


def test_wiz102_dead_end_warns_for_pitch_with_no_children():
    a = UUID(int=30)
    n_a = _node(a, label="Pitch")
    wf = _wf_from_nodes([n_a])
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ102"), None)
    assert f is not None
    assert f.severity is Severity.WARNING


def test_wiz102_does_not_warn_for_unknown_label_leaf():
    a = UUID(int=40)
    n_a = _node(a, label="SomeOtherLabel")  # not in labels_requiring_children
    wf = _wf_from_nodes([n_a])
    findings = check_graph(wf)
    assert not any(f.code == "WIZ102" for f in findings)


def test_wiz103_cycle_is_warning():
    a, b, c = UUID(int=50), UUID(int=51), UUID(int=52)
    n_a = _node(a)
    n_b = _node(b, parent=a)
    n_c = _node(c, parent=b)
    wf = _wf_from_nodes([n_a, n_b, n_c])
    # Add a back-edge c -> a manually
    wf.flow.add_edge(c, a)
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ103"), None)
    assert f is not None
    assert f.severity is Severity.WARNING
