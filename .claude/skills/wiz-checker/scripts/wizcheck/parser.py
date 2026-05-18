"""JSON -> IR parser for WIZ.AI exported dialogue files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from wizcheck.ir import (
    Audio,
    Component,
    ComponentDetails,
    FlowGraph,
    FlowNode,
    Intent,
    Utterance,
    Variable,
    WizFile,
)

_VAR_REF_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ParseError(Exception):
    """Raised on fatal parse failure (malformed JSON, bad ID format, missing required key)."""


def _require(entry: dict[str, Any], key: str, context: str) -> Any:
    if key not in entry:
        raise ParseError(f"{context}: required key '{key}' is missing")
    return entry[key]


def _parse_uuid(value: Any, context: str) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError) as e:
        raise ParseError(f"{context}: '{value}' is not a valid UUID") from e


def _parse_int(value: Any, context: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        raise ParseError(f"{context}: '{value}' is not a valid integer") from e


def parse_file(path: str | Path) -> WizFile:
    """Parse a WIZ.AI exported JSON file and return a fully-populated WizFile."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ParseError(f"{path}: invalid JSON: {e}") from e
    return parse_dict(raw)


def parse_dict(raw: dict[str, Any]) -> WizFile:
    """Parse an already-loaded JSON dict into a WizFile."""
    if not isinstance(raw, dict):
        raise ParseError(
            f"expected a JSON object at top level, got {type(raw).__name__}"
        )
    variables = _parse_variables(raw.get("SpeechVariable", []))
    intents = _parse_intents(raw.get("SpeechIntent", []))
    utterances = _parse_utterances(raw.get("SentenceCutSpeech", []))
    audios = _parse_audios(raw.get("SpeechAudio", []))
    components = _parse_components(raw.get("BizSpeechComponent", []))
    flow = FlowGraph()  # populated in Task 8

    return WizFile(
        raw=raw,
        components=components,
        variables=variables,
        intents=intents,
        utterances=utterances,
        audios=audios,
        flow=flow,
    )


def _parse_variables(entries: list[dict[str, Any]]) -> dict[int, Variable]:
    out: dict[int, Variable] = {}
    for e in entries:
        v = Variable(
            id=_parse_int(_require(e, "id", "SpeechVariable"), "SpeechVariable.id"),
            name=str(_require(e, "name", "SpeechVariable")),
            text_type=str(e.get("textType", "DEFAULT")),
            raw=e,
        )
        out[v.id] = v
    return out


def _parse_intents(entries: list[dict[str, Any]]) -> dict[int, Intent]:
    out: dict[int, Intent] = {}
    for e in entries:
        i = Intent(
            intent_id=_parse_int(_require(e, "intentId", "SpeechIntent"), "SpeechIntent.intentId"),
            name=str(_require(e, "intentName", "SpeechIntent")),
            language=str(e.get("language", "")),
            keywords=tuple(e.get("keyWordInIntent", []) or []),
            user_responses=tuple(e.get("userResponseInIntent", []) or []),
            raw=e,
        )
        out[i.intent_id] = i
    return out


def _parse_utterances(entries: list[dict[str, Any]]) -> tuple[Utterance, ...]:
    out: list[Utterance] = []
    for e in entries:
        text = str(e.get("sentenceText", ""))
        # preserve first-seen order, dedupe
        seen: list[str] = []
        for match in _VAR_REF_RE.finditer(text):
            name = match.group(1)
            if name not in seen:
                seen.append(name)
        u = Utterance(
            id=_parse_uuid(_require(e, "id", "SentenceCutSpeech"), "SentenceCutSpeech.id"),
            component_uuid=_parse_uuid(
                _require(e, "componentUuid", "SentenceCutSpeech"),
                "SentenceCutSpeech.componentUuid",
            ),
            text=text,
            referenced_vars=tuple(seen),
            raw=e,
        )
        out.append(u)
    return tuple(out)


def _parse_audios(entries: list[dict[str, Any]]) -> dict[int, Audio]:
    out: dict[int, Audio] = {}
    for e in entries:
        a = Audio(
            audio_id=_parse_int(_require(e, "audioId", "SpeechAudio"), "SpeechAudio.audioId"),
            name=str(e.get("audioName", "")),
            raw=e,
        )
        out[a.audio_id] = a
    return out


def _parse_components(entries: list[dict[str, Any]]) -> dict[UUID, Component]:
    out: dict[UUID, Component] = {}
    for e in entries:
        comp_uuid = _parse_uuid(
            _require(e, "componentUuid", "BizSpeechComponent"),
            "BizSpeechComponent.componentUuid",
        )
        details = _parse_component_details(e.get("details", ""))
        c = Component(
            uuid=comp_uuid,
            speech_id=int(e.get("speechId", 0)),  # optional, no _parse_int needed
            category=int(e.get("category", 0)),
            branch=str(e.get("branch", "")),
            details=details,
            raw=e,
        )
        out[comp_uuid] = c
    return out


def _parse_component_details(raw_details: str | dict[str, Any] | None) -> ComponentDetails:
    """Parse the escaped-JSON ``details`` string into a ComponentDetails.

    Accepts a dict already-parsed (e.g. from tests), an empty string (treat as
    empty tree), or None.
    """
    if not raw_details:
        return ComponentDetails(flow_nodes={}, root_uuids=())
    if isinstance(raw_details, str):
        try:
            data = json.loads(raw_details)
        except json.JSONDecodeError as e:
            raise ParseError(f"BizSpeechComponent.details is not valid JSON: {e}") from e
    else:
        data = raw_details

    nodes: dict[UUID, FlowNode] = {}
    roots: list[UUID] = []
    for entry in data.get("list", []):
        uuid = _parse_uuid(_require(entry, "uuid", "FlowNode"), "FlowNode.uuid")
        parent_raw = entry.get("parentId")
        parent_uuid = (
            _parse_uuid(parent_raw, "FlowNode.parentId") if parent_raw is not None else None
        )
        node = FlowNode(
            uuid=uuid,
            parent_uuid=parent_uuid,
            label=str(entry.get("label", "")),
            sort_index=int(entry.get("sortIndex", 0)),
            raw=entry,
        )
        nodes[uuid] = node
        if parent_uuid is None:
            roots.append(uuid)
    return ComponentDetails(flow_nodes=nodes, root_uuids=tuple(roots))
