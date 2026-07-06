"""Typed in-memory representation of a WIZ.AI exported dialogue file.

All IR objects are frozen dataclasses and carry a ``raw`` field holding the
unmodified source dict. The FlowModel (populated by parse_dict via
build_flow_model) lives on WizFile.flow_model and is the sole graph
representation. wf.flow_model is None only for WizFile instances constructed
directly in tests without parse_dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from wizcheck.flowmodel import FlowModel


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
class Component:
    """BizSpeechComponent entry: a top-level dialogue component."""

    uuid: UUID
    speech_id: int
    category: int
    branch: str
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
    raw: dict[str, Any] = field(repr=False)
    flow_model: FlowModel | None = field(default=None, kw_only=True)
    is_component_export: bool = field(default=False, kw_only=True)
