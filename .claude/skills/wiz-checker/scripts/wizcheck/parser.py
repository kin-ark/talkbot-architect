"""JSON -> IR parser for WIZ.AI exported dialogue files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from wizcheck.ir import (
    Audio,
    Component,
    ComponentDetails,
    FlowGraph,
    Intent,
    Utterance,
    Variable,
    WizFile,
)


class ParseError(Exception):
    """Raised on fatal parse failure (malformed JSON, bad ID format, missing required key)."""


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
            id=int(e["id"]),
            name=str(e["name"]),
            text_type=str(e.get("textType", "DEFAULT")),
            raw=e,
        )
        out[v.id] = v
    return out


def _parse_intents(entries: list[dict[str, Any]]) -> dict[int, Intent]:
    out: dict[int, Intent] = {}
    for e in entries:
        i = Intent(
            intent_id=int(e["intentId"]),
            name=str(e["intentName"]),
            language=str(e.get("language", "")),
            keywords=tuple(e.get("keyWordInIntent", []) or []),
            user_responses=tuple(e.get("userResponseInIntent", []) or []),
            raw=e,
        )
        out[i.intent_id] = i
    return out


def _parse_utterances(entries: list[dict[str, Any]]) -> tuple[Utterance, ...]:
    # referenced_vars extraction added in Task 6; for now empty
    out: list[Utterance] = []
    for e in entries:
        u = Utterance(
            id=UUID(str(e["id"])),
            component_uuid=UUID(str(e["componentUuid"])),
            text=str(e.get("sentenceText", "")),
            referenced_vars=(),
            raw=e,
        )
        out.append(u)
    return tuple(out)


def _parse_audios(entries: list[dict[str, Any]]) -> dict[int, Audio]:
    out: dict[int, Audio] = {}
    for e in entries:
        a = Audio(
            audio_id=int(e["audioId"]),
            name=str(e.get("audioName", "")),
            raw=e,
        )
        out[a.audio_id] = a
    return out


def _parse_components(entries: list[dict[str, Any]]) -> dict[UUID, Component]:
    # nested details unwrap is Task 5; for now use empty ComponentDetails
    out: dict[UUID, Component] = {}
    for e in entries:
        comp_uuid = UUID(str(e["componentUuid"]))
        details = ComponentDetails(flow_nodes={}, root_uuids=())
        c = Component(
            uuid=comp_uuid,
            speech_id=int(e.get("speechId", 0)),
            category=int(e.get("category", 0)),
            branch=str(e.get("branch", "")),
            details=details,
            raw=e,
        )
        out[comp_uuid] = c
    return out
