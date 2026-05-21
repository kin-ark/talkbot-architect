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


def _node(uid, parent=None, label="Other", raw_children=None) -> FlowNode:
    raw = {"children": raw_children} if raw_children is not None else {}
    return FlowNode(uuid=uid, parent_uuid=parent, label=label, sort_index=0, raw=raw)


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


def test_wiz100_orphan_parent_is_warning_not_error():
    """v3: orphan parent refs are warnings (likely Component Library imports)."""
    a, missing = UUID(int=10), UUID(int=11)
    n_a = _node(a)
    n_orphan_ref = _node(UUID(int=12), parent=missing, label="ASR Corpus Collection")
    wf = _wf_from_nodes([n_a, n_orphan_ref])
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ100"), None)
    assert f is not None
    assert f.severity is Severity.WARNING
    assert str(missing) in f.message or str(missing) in (f.location.id or "")


def test_wiz100_message_includes_child_labels():
    """v3: WIZ100 message hints at the referenced library component via the child's label."""
    a, missing = UUID(int=10), UUID(int=11)
    n_a = _node(a)
    n_orphan_ref = _node(UUID(int=12), parent=missing, label="ASR Corpus Collection")
    wf = _wf_from_nodes([n_a, n_orphan_ref])
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ100"), None)
    assert f is not None
    assert "ASR Corpus Collection" in f.message


def test_wiz101_descendants_of_library_ref_are_not_unreachable():
    """v3: a node whose only path to a root goes through a library-ref orphan is reachable.

    The orphan parent is treated as an external root.
    """
    a = UUID(int=20)
    orphan_parent = UUID(int=21)
    child = UUID(int=22)
    grandchild = UUID(int=23)
    n_a = _node(a)
    n_child = _node(child, parent=orphan_parent, label="Library Entry")
    n_grandchild = _node(grandchild, parent=child)
    wf = _wf_from_nodes([n_a, n_child, n_grandchild])
    findings = check_graph(wf)
    # Neither child nor grandchild should be flagged as unreachable.
    assert not any(
        f.code == "WIZ101" and str(child) in (f.location.id or "")
        for f in findings
    )
    assert not any(
        f.code == "WIZ101" and str(grandchild) in (f.location.id or "")
        for f in findings
    )


def test_wiz101_genuinely_disconnected_node_is_warning():
    """A node not reachable from any root (declared OR library-ref) still fires WIZ101."""
    a, b = UUID(int=50), UUID(int=51)
    n_a = FlowNode(uuid=a, parent_uuid=None, label="Greeting", sort_index=0, raw={})
    n_b = FlowNode(uuid=b, parent_uuid=None, label="Disconnected", sort_index=0, raw={})
    # Construct WizFile manually so only `a` is a declared root (b is NOT).
    comp = Component(
        uuid=UUID(int=1), speech_id=1, category=1, branch="dev",
        details=ComponentDetails(flow_nodes={a: n_a, b: n_b}, root_uuids=(a,)),
        raw={"createTime": 1700000000000, "updateTime": 1700000000000},
    )
    g = FlowGraph()
    g.add_node(a)
    g.add_node(b)
    # No edges; no orphan parents either.
    wf = WizFile(
        raw={},
        components={comp.uuid: comp},
        variables={}, intents={}, utterances=(), audios={},
        flow=g,
    )
    findings = check_graph(wf)
    assert any(
        f.code == "WIZ101" and str(b) in (f.location.id or "")
        for f in findings
    )


def test_wiz104_rollup_present_when_library_refs_exist():
    """v3: WIZ104 emits one rollup finding when at least one orphan parent exists."""
    a, missing = UUID(int=60), UUID(int=61)
    n_a = _node(a)
    n_child = _node(UUID(int=62), parent=missing, label="Re-ask Limit")
    wf = _wf_from_nodes([n_a, n_child])
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ104"), None)
    assert f is not None
    assert f.severity is Severity.WARNING
    assert "Re-ask Limit" in f.message


def test_wiz104_absent_when_no_library_refs():
    """No orphan parents → no WIZ104."""
    a, b = UUID(int=70), UUID(int=71)
    n_a = _node(a)
    n_b = _node(b, parent=a)  # b's parent IS present
    wf = _wf_from_nodes([n_a, n_b])
    findings = check_graph(wf)
    assert not any(f.code == "WIZ104" for f in findings)


def test_wiz104_rollup_dedupes_labels():
    """Multiple children of the same library ref with the same label produce one label entry."""
    a = UUID(int=80)
    missing = UUID(int=81)
    c1, c2 = UUID(int=82), UUID(int=83)
    n_a = _node(a)
    n_c1 = _node(c1, parent=missing, label="Re-ask Limit")
    n_c2 = _node(c2, parent=missing, label="Re-ask Limit")
    wf = _wf_from_nodes([n_a, n_c1, n_c2])
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ104"), None)
    assert f is not None
    # Label should appear exactly once in the message, even though two children share it.
    assert f.message.count("Re-ask Limit") == 1


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


def test_wiz102_skips_node_with_raw_children():
    """A FlowNode with non-empty raw['children'] is not a dead-end.

    Even if parentId-based edges don't connect it to children.
    """
    a = UUID(int=100)
    n_a = _node(a, label="Pitch", raw_children=[{"uuid": "fake"}])
    wf = _wf_from_nodes([n_a])
    findings = check_graph(wf)
    # 'Pitch' is in labels_requiring_children, but visual children should suppress WIZ102
    assert not any(f.code == "WIZ102" for f in findings)


def test_wiz102_still_fires_for_node_with_no_raw_children():
    """A leaf 'Pitch' with no raw.children still fires WIZ102."""
    a = UUID(int=101)
    n_a = _node(a, label="Pitch")  # raw_children defaults to None
    wf = _wf_from_nodes([n_a])
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ102"), None)
    assert f is not None


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


def test_wiz104_rollup_message_clarifies_when_refs_exceed_distinct_labels():
    """When two orphan parents share a child label, the message names both counts."""
    a = UUID(int=90)
    missing1, missing2 = UUID(int=91), UUID(int=92)
    c1, c2 = UUID(int=93), UUID(int=94)
    n_a = _node(a)
    n_c1 = _node(c1, parent=missing1, label="Re-ask Limit")
    n_c2 = _node(c2, parent=missing2, label="Re-ask Limit")
    wf = _wf_from_nodes([n_a, n_c1, n_c2])
    findings = check_graph(wf)
    f = next((x for x in findings if x.code == "WIZ104"), None)
    assert f is not None
    # 2 distinct orphan parents, 1 distinct label
    assert "2 external/library reference(s) to 1 distinct component(s)" in f.message


def test_library_ref_fixture_emits_warnings_not_errors(fixture_path):
    """End-to-end: library_ref.json produces WIZ100 + WIZ104 warnings, no errors."""
    from wizcheck.parser import parse_file
    wf = parse_file(fixture_path("library_ref.json"))
    findings = check_graph(wf)
    codes = [f.code for f in findings]
    assert "WIZ100" in codes
    assert "WIZ104" in codes
    # No graph-layer errors — everything is a warning under v3.
    assert not any(f.severity is Severity.ERROR for f in findings)
    # The ASR Corpus Collection label should appear in the WIZ104 rollup message.
    f104 = next(f for f in findings if f.code == "WIZ104")
    assert "ASR Corpus Collection" in f104.message
