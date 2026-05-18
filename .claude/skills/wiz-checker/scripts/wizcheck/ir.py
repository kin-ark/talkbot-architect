"""Typed in-memory representation of a WIZ.AI exported dialogue file.

All IR objects are frozen dataclasses and carry a ``raw`` field holding the
unmodified source dict. The FlowGraph (added in Task 3) lives on WizFile.flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Variable:
    """SpeechVariable entry: a named runtime substitution slot."""

    id: int
    name: str
    text_type: str
    raw: dict[str, Any] = field(repr=False)


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
class WizFile:
    """Top-level container for a parsed WIZ.AI exported JSON file."""

    components: dict[UUID, Component]
    variables: dict[int, Variable]
    intents: dict[int, Intent]
    utterances: tuple[Utterance, ...]
    audios: dict[int, Audio]
    flow: Any  # FlowGraph; typed in Task 3. Kept as Any to avoid forward-ref noise.
    raw: dict[str, Any] = field(repr=False)
