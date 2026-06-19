"""Typed in-memory representation of a WIZ.AI exported dialogue file.

All IR objects are frozen dataclasses and carry a ``raw`` field holding the
unmodified source dict. The FlowGraph (added in Task 3) lives on WizFile.flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import networkx as nx


@dataclass(frozen=True)
class Variable:
    """SpeechVariable entry: a named runtime substitution slot."""

    id: int
    name: str
    text_type: str
    raw: dict[str, Any] = field(repr=False)
    variable_source: int = 0  # 0 = user-authored, 1 = platform/system-managed


@dataclass(frozen=True)
class Intent:
    """SpeechIntent entry: an intent classifier like 'Negative' or 'DNC'."""

    intent_id: int
    name: str
    language: str
    keywords: tuple[str, ...]
    user_responses: tuple[str, ...]
    raw: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class Utterance:
    """SentenceCutSpeech entry: one sentence fragment with optional {var} refs."""

    id: UUID
    component_uuid: UUID
    text: str
    referenced_vars: tuple[str, ...]
    raw: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class FlowNode:
    """One entry inside BizSpeechComponent.details.list — a node in the flow tree."""

    uuid: UUID
    parent_uuid: UUID | None
    label: str
    sort_index: int
    raw: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class ComponentDetails:
    """Parsed contents of the escaped-JSON ``details`` field on a Component."""

    flow_nodes: dict[UUID, FlowNode]
    root_uuids: tuple[UUID, ...]


@dataclass(frozen=True)
class Component:
    """BizSpeechComponent entry: a top-level dialogue component."""

    uuid: UUID
    speech_id: int
    category: int
    branch: str
    details: ComponentDetails
    raw: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class Audio:
    """SpeechAudio (plus linked VoiceRecord) entry. Stub for v1 (no checks consume yet).

    VoiceRecord fields are not promoted to typed attributes in v1; access them
    via ``raw`` if needed (e.g. ``audio.raw.get('voiceRecord', {})``).
    """

    audio_id: int
    name: str
    raw: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class KnowledgeBase:
    """BizKnowledgeInfo entry: A system or user-defined FAQ/Knowledge Base."""

    knowledge_id: int
    title: str
    kd_type: int
    intents: tuple[int, ...]
    raw: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class WizFile:
    """Top-level container for a parsed WIZ.AI exported JSON file."""

    components: dict[UUID, Component]
    variables: dict[int, Variable]
    intents: dict[int, Intent]
    utterances: tuple[Utterance, ...]
    audios: dict[int, Audio]
    knowledge_bases: dict[int, KnowledgeBase]
    flow: FlowGraph
    raw: dict[str, Any] = field(repr=False)


class FlowGraph:
    """Directed graph over FlowNodes across all Components.

    Nodes are FlowNode UUIDs. Edges are parent->child relationships.
    Nodes added explicitly via add_node() carry attribute present=True; nodes
    that appear only as edge endpoints (i.e. orphan references) have
    present=False and surface via orphan_refs().
    """

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()

    def add_node(self, uuid: UUID) -> None:
        self._g.add_node(uuid, present=True)

    def add_edge(self, parent: UUID, child: UUID) -> None:
        # Ensure both endpoints exist; an unknown endpoint is marked absent
        if parent not in self._g:
            self._g.add_node(parent, present=False)
        if child not in self._g:
            self._g.add_node(child, present=False)
        self._g.add_edge(parent, child)

    def reachable_from(self, start: UUID) -> set[UUID]:
        if start not in self._g:
            return set()
        return {start, *nx.descendants(self._g, start)}

    def orphan_refs(self) -> list[UUID]:
        return [n for n, attrs in self._g.nodes(data=True) if not attrs.get("present", False)]

    def library_refs(self) -> dict[UUID, list[UUID]]:
        """Return {orphan_parent_uuid: [child_uuid, ...]} for every unresolved parent.

        These represent references to nodes outside this export — typically WIZ.AI
        Component Library imports (e.g., ASR Corpus Collection, Re-ask Limit), but
        possibly malformed parent links. Used by WIZ100 / WIZ101 / WIZ104 to
        reason about external references.
        """
        return {
            orphan: list(self._g.successors(orphan))
            for orphan in self.orphan_refs()
        }

    def dead_ends(self) -> list[UUID]:
        return [
            n for n, attrs in self._g.nodes(data=True)
            if attrs.get("present", False) and self._g.out_degree(n) == 0
        ]

    def cycles(self) -> list[list[UUID]]:
        return [list(c) for c in nx.simple_cycles(self._g)]

    def all_nodes(self) -> set[UUID]:
        return {n for n, attrs in self._g.nodes(data=True) if attrs.get("present", False)}

    @property
    def graph(self) -> nx.DiGraph:
        """Access the underlying networkx graph for read-only algorithm use.

        WARNING: Mutating the returned graph directly bypasses the present/orphan
        bookkeeping maintained by add_node and add_edge. Callers must use the
        provided mutators (add_node, add_edge) to modify the graph.
        """
        return self._g
