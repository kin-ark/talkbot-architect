"""Tests for checks.graph rewritten onto FlowModel (WIZ100..WIZ104).

All fixtures are built via parse_dict() so wf.flow_model is populated.
The real WIZ export format uses UUID-keyed envelope dicts in details plus
a routes dict mapping source-node-uuid -> port-uuid -> {target: {uuid: ...}}.

TDD order:
  1. Write failing tests (RED)
  2. Implement check_graph on FlowModel
  3. All tests pass (GREEN)
"""

from __future__ import annotations

import json

from wizcheck.checks.graph import check_graph
from wizcheck.parser import parse_dict
from wizcheck.report import Severity

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_export(
    *,
    comp_uuid: str = "aaaa0000-0000-4000-8000-000000000000",
    nodes: dict,      # {node_uuid: envelope_dict}
    routes: dict,     # {node_uuid: {port_uuid: {target: {uuid: ...}}}}
    kb_ids: list[int] | None = None,
) -> dict:
    """Build a minimal real-format WIZ export dict parseable by parse_dict()."""
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
    """Build a minimal talk-node envelope dict for the real WIZ format."""
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
    """Build a minimal exit-node (type 2) envelope dict."""
    return {
        "name": name,
        "is_default": False,
        "type": 2,
        "data": {
            "name": name,
            "type": 2,
            "is_transfer": 0,
            "list": [],
        },
    }


def _goto_comp_envelope(target_comp_uuid: str, name: str = "Go To Component") -> dict:
    """Build a goto_component (type 4) envelope dict."""
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
    """Build a goto_kb (type 8) envelope dict."""
    return {
        "name": name,
        "is_default": False,
        "type": 8,
        "data": {
            "name": name,
            "type": 8,
            "appoint_knowledge_id": kb_id,
        },
    }


# ---------------------------------------------------------------------------
# Guard: flow_model is None -> return []
# ---------------------------------------------------------------------------

class TestFlowModelNoneGuard:
    def test_returns_empty_when_flow_model_is_none(self):
        """check_graph returns [] when wf.flow_model is None (direct WizFile construction)."""
        from uuid import UUID

        from wizcheck.ir import Component, WizFile
        comp = Component(
            uuid=UUID(int=1), speech_id=1, category=1, branch="dev",
            raw={},
        )
        wf = WizFile(
            raw={},
            components={comp.uuid: comp},
            variables={}, intents={}, utterances=(), audios={}, knowledge_bases={},
            flow_model=None,
        )
        assert check_graph(wf) == []


# ---------------------------------------------------------------------------
# WIZ100: orphan refs
# ---------------------------------------------------------------------------

class TestWIZ100OrphanRefs:
    def test_wiz100_fires_for_target_uuid_not_in_component(self):
        """WIZ100: a branch.target_uuid absent from the component's nodes triggers a WARNING."""
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
        assert f is not None, f"Expected WIZ100, got: {[x.code for x in findings]}"
        assert f.severity is Severity.WARNING
        assert "node-missing" in f.message

    def test_wiz100_absent_when_all_targets_present(self):
        """No WIZ100 when all target_uuids exist in the component."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("Greeting", is_default=True, ports=["port-1"]),
                "node-b": _talk_envelope("Pitch", ports=[]),
            },
            routes={
                "node-a": {"port-1": {"target": {"uuid": "node-b"}}},
            },
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ100" for f in findings)

    def test_wiz100_does_not_fire_for_target_component(self):
        """Cross-component jumps (target_component) are NOT orphans — no WIZ100."""
        other_comp = "bbbb0000-0000-4000-8000-000000000000"
        data = _make_export(
            nodes={
                "node-a": _goto_comp_envelope(other_comp, "Go To Pitch"),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ100" for f in findings)

    def test_wiz100_does_not_fire_for_terminal_exit(self):
        """Terminal (hangup/transfer) nodes are not orphans — no WIZ100."""
        data = _make_export(
            nodes={
                "node-a": _exit_envelope("Hang Up"),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ100" for f in findings)

    def test_wiz100_does_not_fire_for_target_kb(self):
        """KB jumps (target_kb) are not orphans — no WIZ100."""
        data = _make_export(
            nodes={
                "node-a": _goto_kb_envelope(12345, "Go To FAQ"),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ100" for f in findings)


# ---------------------------------------------------------------------------
# WIZ101: unreachable nodes
# ---------------------------------------------------------------------------

class TestWIZ101Unreachable:
    def test_wiz101_fires_for_disconnected_node(self):
        """WIZ101 fires when node-b has no incoming edge from the entry node."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("Greeting", is_default=True),
                "node-b": _talk_envelope("Disconnected"),
            },
            routes={},  # no edge from node-a to node-b
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        f = next((x for x in findings if x.code == "WIZ101"), None)
        assert f is not None, f"Expected WIZ101, got: {[x.code for x in findings]}"
        assert f.severity is Severity.WARNING
        assert "node-b" in f.message

    def test_wiz101_absent_when_node_reachable(self):
        """No WIZ101 when entry->node-b via a branch (node-b is reachable)."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("Greeting", is_default=True, ports=["port-1"]),
                "node-b": _talk_envelope("Pitch"),
            },
            routes={
                "node-a": {"port-1": {"target": {"uuid": "node-b"}}},
            },
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ101" for f in findings)

    def test_wiz101_skipped_when_no_entry_node(self):
        """When no node has is_default=True, root_uuids is empty — skip reachability check."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("A"),
                "node-b": _talk_envelope("B"),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        # No root_uuids means we cannot determine reachability — WIZ101 must NOT fire.
        assert not any(f.code == "WIZ101" for f in findings)

    def test_wiz101_only_flags_unreachable_not_entry(self):
        """WIZ101 flags node-c but not node-a (entry) or node-b (reachable from entry)."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("Greeting", is_default=True, ports=["port-1"]),
                "node-b": _talk_envelope("Pitch"),
                "node-c": _talk_envelope("Orphan"),
            },
            routes={
                "node-a": {"port-1": {"target": {"uuid": "node-b"}}},
            },
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        wiz101 = [f for f in findings if f.code == "WIZ101"]
        assert len(wiz101) == 1
        assert "node-c" in wiz101[0].message


# ---------------------------------------------------------------------------
# WIZ102: dead-ends
# ---------------------------------------------------------------------------

class TestWIZ102DeadEnds:
    def test_wiz102_fires_for_pitch_leaf(self):
        """WIZ102 warns when a node labelled 'Pitch' has no outgoing branch."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("Pitch", is_default=True, ports=[]),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        f = next((x for x in findings if x.code == "WIZ102"), None)
        assert f is not None, f"Expected WIZ102, got: {[x.code for x in findings]}"
        assert f.severity is Severity.WARNING
        assert "Pitch" in f.message

    def test_wiz102_fires_for_greeting_leaf(self):
        """WIZ102 warns for 'Greeting' leaf node (in labels_requiring_children)."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("Greeting", is_default=True, ports=[]),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert any(f.code == "WIZ102" and "Greeting" in f.message for f in findings)

    def test_wiz102_absent_for_unknown_label_leaf(self):
        """WIZ102 does NOT fire for leaf nodes whose label is not in the allowlist."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("SomeUnlistedLabel", is_default=True, ports=[]),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ102" for f in findings)

    def test_wiz102_absent_when_node_has_target(self):
        """WIZ102 does NOT fire for a 'Pitch' node that does have a target."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("Pitch", is_default=True, ports=["port-1"]),
                "node-b": _talk_envelope("Next", ports=[]),
            },
            routes={
                "node-a": {"port-1": {"target": {"uuid": "node-b"}}},
            },
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ102" for f in findings)

    def test_wiz102_absent_for_terminal_node(self):
        """A terminal exit node has no targets but is not a dead-end (terminal=hangup)."""
        data = _make_export(
            nodes={
                "node-exit": _exit_envelope("Hang Up"),
            },
            routes={},
        )
        wf = parse_dict(data)
        # Exit node has no target but it's terminal — should not fire WIZ102
        # unless "Hang Up" is in labels_requiring_children (it isn't)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ102" for f in findings)

    def test_wiz102_absent_for_goto_component_leaf(self):
        """A goto_component node has no same-component target but is an intentional exit."""
        other = "bbbb0000-0000-4000-8000-000000000000"
        data = _make_export(
            nodes={
                "node-a": _goto_comp_envelope(other, "Pitch"),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        # "Pitch" label IS in labels_requiring_children but goto_component has target_component
        assert not any(f.code == "WIZ102" for f in findings)


# ---------------------------------------------------------------------------
# WIZ103: cycles
# ---------------------------------------------------------------------------

class TestWIZ103Cycles:
    def test_wiz103_fires_for_two_node_cycle(self):
        """WIZ103 fires when a->b->a forms a directed cycle within a component."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("A", is_default=True, ports=["port-a"]),
                "node-b": _talk_envelope("B", ports=["port-b"]),
            },
            routes={
                "node-a": {"port-a": {"target": {"uuid": "node-b"}}},
                "node-b": {"port-b": {"target": {"uuid": "node-a"}}},
            },
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        f = next((x for x in findings if x.code == "WIZ103"), None)
        assert f is not None, f"Expected WIZ103, got: {[x.code for x in findings]}"
        assert f.severity is Severity.WARNING

    def test_wiz103_absent_for_linear_flow(self):
        """No WIZ103 when flow is a->b->c with no back edges."""
        data = _make_export(
            nodes={
                "node-a": _talk_envelope("A", is_default=True, ports=["port-a"]),
                "node-b": _talk_envelope("B", ports=["port-b"]),
                "node-c": _talk_envelope("C", ports=[]),
            },
            routes={
                "node-a": {"port-a": {"target": {"uuid": "node-b"}}},
                "node-b": {"port-b": {"target": {"uuid": "node-c"}}},
            },
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ103" for f in findings)

    def test_wiz103_cross_component_not_a_cycle(self):
        """A cross-component edge (target_component) is excluded from cycle detection."""
        other = "bbbb0000-0000-4000-8000-000000000000"
        data = _make_export(
            nodes={
                "node-a": _goto_comp_envelope(other, "Go To Other"),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ103" for f in findings)


# ---------------------------------------------------------------------------
# WIZ104: library refs rollup
# ---------------------------------------------------------------------------

class TestWIZ104LibraryRefsRollup:
    def test_wiz104_fires_for_external_component_ref(self):
        """WIZ104 fires when a goto_component targets a component UUID not in the model."""
        other = "bbbb0000-0000-4000-8000-000000000000"
        data = _make_export(
            nodes={
                "node-a": _goto_comp_envelope(other, "Go To External"),
            },
            routes={},
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        f = next((x for x in findings if x.code == "WIZ104"), None)
        assert f is not None, f"Expected WIZ104, got: {[x.code for x in findings]}"
        assert f.severity is Severity.WARNING

    def test_wiz104_fires_for_external_kb_ref(self):
        """WIZ104 fires when a goto_kb targets a knowledge_id not in BizKnowledgeInfo."""
        data = _make_export(
            nodes={
                "node-a": _goto_kb_envelope(99999, "Go To Missing KB"),
            },
            routes={},
            # kb_ids intentionally empty — 99999 is not in the model
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        f = next((x for x in findings if x.code == "WIZ104"), None)
        assert f is not None
        assert f.severity is Severity.WARNING

    def test_wiz104_absent_when_target_component_known(self):
        """No WIZ104 when the target_component exists in the same export."""
        comp_a = "aaaa0000-0000-4000-8000-000000000000"
        comp_b = "bbbb0000-0000-4000-8000-000000000000"
        data = {
            "BizSpeechComponent": [
                {
                    "componentUuid": comp_a,
                    "speechId": 1,
                    "category": 1,
                    "branch": "dev",
                    "details": json.dumps({
                        "node-a": _goto_comp_envelope(comp_b, "Go To B"),
                    }),
                    "routes": json.dumps({}),
                },
                {
                    "componentUuid": comp_b,
                    "speechId": 2,
                    "category": 1,
                    "branch": "dev",
                    "details": json.dumps({
                        "node-b": _talk_envelope("Entry B", is_default=True),
                    }),
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

    def test_wiz104_absent_when_target_kb_known(self):
        """No WIZ104 when the target_kb knowledge_id exists in BizKnowledgeInfo."""
        data = _make_export(
            nodes={
                "node-a": _goto_kb_envelope(12345, "Go To Known KB"),
            },
            routes={},
            kb_ids=[12345],
        )
        wf = parse_dict(data)
        findings = check_graph(wf)
        assert not any(f.code == "WIZ104" for f in findings)
