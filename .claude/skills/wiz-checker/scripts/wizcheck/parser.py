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
    Intent,
    KnowledgeBase,
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


def _unwrap_list(raw: Any, key: str) -> list[dict[str, Any]]:
    """Return a list value from *raw*.

    Real WIZ exports store most top-level collection values as JSON-encoded
    strings (e.g. ``"SpeechVariable": "[{...}]"``).  Test fixtures use
    already-parsed lists.  This helper normalises both formats.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        if not raw.strip():
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(f"{key}: JSON-string value is not valid JSON: {exc}") from exc
        if not isinstance(parsed, list):
            raise ParseError(f"{key}: expected a JSON array, got {type(parsed).__name__}")
        return parsed  # type: ignore[return-value]
    if isinstance(raw, list):
        return raw  # type: ignore[return-value]
    raise ParseError(f"{key}: expected a list or JSON-array string, got {type(raw).__name__}")


_BRACKET_LIST_RE = re.compile(r"^\[(.+)\]$", re.DOTALL)


def _unwrap_keyword_list(raw: Any, key: str) -> list[str]:
    """Return a list of keyword strings from *raw*.

    Intent keyword/response fields come in three forms:
    - Already a list (test fixtures).
    - A JSON-encoded array string: ``'["a","b"]'``.
    - A WIZ bracket-delimited string: ``'[a;b;c]'`` or ``'[a,b,c]'``
      (not valid JSON — items are separated by ``;`` or ``,``).

    Returns an empty list for None or empty/whitespace strings.
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if not isinstance(raw, str):
        raise ParseError(f"{key}: expected a list or string, got {type(raw).__name__}")
    stripped = raw.strip()
    if not stripped:
        return []
    # Try JSON first (handles ``["a","b"]`` arrays from newer exports).
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        raise ParseError(f"{key}: expected a JSON array, got {type(parsed).__name__}")
    except json.JSONDecodeError:
        pass
    # Fall back to WIZ bracket-delimited format: ``[item1;item2]`` or ``[item1,item2]``.
    m = _BRACKET_LIST_RE.match(stripped)
    if m:
        inner = m.group(1)
        # Prefer semicolon splitting; fall back to comma if no semicolons present.
        sep = ";" if ";" in inner else ","
        return [item.strip() for item in inner.split(sep) if item.strip()]
    # Plain unbracketed string — treat as single-item list.
    return [stripped]


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

    from wizcheck.component_adapter import component_export_to_full, is_component_export
    component_mode = is_component_export(raw)
    if component_mode:
        raw = component_export_to_full(raw)

    variables = _parse_variables(_unwrap_list(raw.get("SpeechVariable"), "SpeechVariable"))
    intents = _parse_intents(_unwrap_list(raw.get("SpeechIntent"), "SpeechIntent"))
    utterances = _parse_utterances(
        _unwrap_list(raw.get("SentenceCutSpeech"), "SentenceCutSpeech")
    )
    audios = _parse_audios(_unwrap_list(raw.get("SpeechAudio"), "SpeechAudio"))
    components = _parse_components(
        _unwrap_list(raw.get("BizSpeechComponent"), "BizSpeechComponent")
    )
    knowledge_bases = _parse_knowledge_bases(
        _unwrap_list(raw.get("BizKnowledgeInfo"), "BizKnowledgeInfo")
    )

    from wizcheck.flowmodel import build_flow_model
    flow_model = build_flow_model(raw)

    return WizFile(
        raw=raw,
        components=components,
        variables=variables,
        intents=intents,
        utterances=utterances,
        audios=audios,
        knowledge_bases=knowledge_bases,
        flow_model=flow_model,
        is_component_export=component_mode,
    )



def _parse_variables(entries: list[dict[str, Any]]) -> dict[int, Variable]:
    out: dict[int, Variable] = {}
    for e in entries:
        v = Variable(
            id=_parse_int(_require(e, "id", "SpeechVariable"), "SpeechVariable.id"),
            name=str(_require(e, "name", "SpeechVariable")),
            text_type=str(e.get("textType", "DEFAULT")),
            raw=e,
            variable_source=int(e.get("variableSource", 0)),
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
            keywords=tuple(
                _unwrap_keyword_list(e.get("keyWordInIntent"), "SpeechIntent.keyWordInIntent")
            ),
            user_responses=tuple(
                _unwrap_keyword_list(
                    e.get("userResponseInIntent"), "SpeechIntent.userResponseInIntent"
                )
            ),
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


def _parse_knowledge_bases(entries: list[dict[str, Any]]) -> dict[int, KnowledgeBase]:
    out: dict[int, KnowledgeBase] = {}
    for e in entries:
        intents_raw = _unwrap_list(e.get("intents"), "BizKnowledgeInfo.intents")
        intents_list = []
        for intent in intents_raw:
            if isinstance(intent, dict) and "intentId" in intent:
                intents_list.append(
                    _parse_int(intent["intentId"], "BizKnowledgeInfo.intents.intentId")
                )

        kb = KnowledgeBase(
            knowledge_id=_parse_int(
                _require(e, "knowledgeId", "BizKnowledgeInfo"), "BizKnowledgeInfo.knowledgeId"
            ),
            title=str(e.get("kdTitle", e.get("title", ""))),
            kd_type=_parse_int(e.get("kdType", 0), "BizKnowledgeInfo.kdType"),
            intents=tuple(intents_list),
            raw=e,
        )
        out[kb.knowledge_id] = kb
    return out



def _parse_components(entries: list[dict[str, Any]]) -> dict[UUID, Component]:
    out: dict[UUID, Component] = {}
    for e in entries:
        comp_uuid = _parse_uuid(
            _require(e, "componentUuid", "BizSpeechComponent"),
            "BizSpeechComponent.componentUuid",
        )
        c = Component(
            uuid=comp_uuid,
            speech_id=int(e.get("speechId", 0)),  # optional, no _parse_int needed
            category=int(e.get("category", 0)),
            branch=str(e.get("branch", "")),
            raw=e,
        )
        out[comp_uuid] = c
    return out
