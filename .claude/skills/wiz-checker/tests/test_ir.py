"""Tests for the in-memory IR types in wizcheck.ir."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest
from wizcheck.ir import (
    ComponentDetails,
    FlowGraph,
    FlowNode,
    Intent,
    Utterance,
    Variable,
    WizFile,
)

UUID_A = UUID("00000000-0000-4000-8000-000000000001")
UUID_B = UUID("00000000-0000-4000-8000-000000000002")


def test_variable_is_frozen_and_has_raw():
    v = Variable(id=1, name="Phone", text_type="PHONE", raw={"id": 1, "name": "Phone"})
    assert v.id == 1
    assert v.name == "Phone"
    assert v.text_type == "PHONE"
    assert v.raw["name"] == "Phone"
    with pytest.raises(FrozenInstanceError):
        v.id = 2  # frozen dataclass must not allow mutation


def test_intent_carries_keywords_and_responses():
    i = Intent(
        intent_id=460827,
        name="Negative",
        language="IDN",
        keywords=("tidak", "nggak"),
        user_responses=("tidak mau",),
        raw={"intentId": 460827, "intentName": "Negative"},
    )
    assert i.name == "Negative"
    assert "tidak" in i.keywords


def test_utterance_referenced_vars_is_tuple():
    u = Utterance(
        id=UUID_A,
        component_uuid=UUID_B,
        text="Halo {Name}, selamat datang.",
        referenced_vars=("Name",),
        raw={"id": str(UUID_A)},
    )
    assert u.referenced_vars == ("Name",)


def test_flownode_root_has_no_parent():
    n = FlowNode(uuid=UUID_A, parent_uuid=None, label="Greetings", sort_index=0, raw={})
    assert n.parent_uuid is None


def test_component_details_can_be_empty():
    d = ComponentDetails(flow_nodes={}, root_uuids=())
    assert d.flow_nodes == {}
    assert d.root_uuids == ()


def test_wizfile_holds_all_collections():
    wf = WizFile(
        components={},
        variables={},
        intents={},
        utterances=(),
        audios={},
        flow=None,
        raw={},
    )
    assert wf.components == {}
    assert wf.utterances == ()


def _build_graph(edges: list[tuple[UUID, UUID]], all_nodes: list[UUID]) -> FlowGraph:
    g = FlowGraph()
    for n in all_nodes:
        g.add_node(n)
    for parent, child in edges:
        g.add_edge(parent, child)
    return g


def test_flowgraph_reachable_from_walks_descendants():
    a, b, c, d = (UUID(int=i) for i in range(1, 5))
    g = _build_graph([(a, b), (b, c)], [a, b, c, d])
    assert g.reachable_from(a) == {a, b, c}
    assert d not in g.reachable_from(a)


def test_flowgraph_orphan_refs_finds_referenced_but_missing():
    a, b = UUID(int=10), UUID(int=11)
    g = FlowGraph()
    g.add_node(a)
    g.add_edge(a, b)  # b is referenced but not added
    assert b in g.orphan_refs()


def test_flowgraph_dead_ends_finds_leaves():
    a, b, c = UUID(int=20), UUID(int=21), UUID(int=22)
    g = _build_graph([(a, b), (a, c)], [a, b, c])
    leaves = g.dead_ends()
    assert b in leaves
    assert c in leaves
    assert a not in leaves


def test_flowgraph_cycles_detects_simple_cycle():
    a, b, c = UUID(int=30), UUID(int=31), UUID(int=32)
    g = _build_graph([(a, b), (b, c), (c, a)], [a, b, c])
    cycles = g.cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {a, b, c}
