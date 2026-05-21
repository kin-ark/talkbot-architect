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
    variables = _parse_variables(_unwrap_list(raw.get("SpeechVariable"), "SpeechVariable"))
    intents = _parse_intents(_unwrap_list(raw.get("SpeechIntent"), "SpeechIntent"))
    utterances = _parse_utterances(
        _unwrap_list(raw.get("SentenceCutSpeech"), "SentenceCutSpeech")
    )
    audios = _parse_audios(_unwrap_list(raw.get("SpeechAudio"), "SpeechAudio"))
    components = _parse_components(
        _unwrap_list(raw.get("BizSpeechComponent"), "BizSpeechComponent")
    )
    flow = _build_flow_graph(components)

    return WizFile(
        raw=raw,
        components=components,
        variables=variables,
        intents=intents,
        utterances=utterances,
        audios=audios,
        flow=flow,
    )


def _build_flow_graph(components: dict[UUID, Component]) -> FlowGraph:
    """Build a FlowGraph from all components' FlowNodes.

    Two-pass: first register every known node as present, then add parent->child
    edges. add_edge will mark unknown endpoints as orphan refs (present=False).
    """
    g = FlowGraph()
    # First pass: register all known nodes.
    for comp in components.values():
        for node_uuid in comp.details.flow_nodes:
            g.add_node(node_uuid)
    # Second pass: add edges. add_edge marks unknown endpoints as orphans.
    for comp in components.values():
        for node in comp.details.flow_nodes.values():
            if node.parent_uuid is not None:
                g.add_edge(node.parent_uuid, node.uuid)
    return g


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


def _is_legacy_details(data: dict) -> bool:
    """Legacy fixture format: {'list': [...]} with no UUID-shaped keys."""
    if not isinstance(data.get("list"), list):
        return False
    # Real-format envelopes have UUID-shaped keys at the top level alongside any "list"
    for key in data:
        if key == "list":
            continue
        try:
            UUID(str(key))
            return False  # found a UUID key -> real format
        except (ValueError, TypeError):
            pass
    return True


def _parse_component_details(raw_details: str | dict[str, Any] | None) -> ComponentDetails:
    """Parse the ``details`` field of a BizSpeechComponent into a ComponentDetails.

    Two formats are accepted:

    *Legacy / fixture format* — the JSON string decodes to a dict with a
    ``"list"`` key whose value is a flat list of FlowNode dicts::

        {"list": [{"uuid": "...", "parentId": null, ...}, ...]}

    *Real WIZ export format* — the JSON string decodes to a dict keyed by node
    UUID, where each value is a node envelope with the flow-node list nested at
    ``canvas.component.props.list``.  ``parentId`` is ``""`` (empty string) for
    root nodes instead of ``null``::

        {"<uuid>": {"canvas": {"component": {"props": {"list": [...]}}}}, ...}

    Both formats are normalised into the same ``ComponentDetails``.
    Accepts an already-parsed dict (e.g. from unit tests), an empty/None value
    (returns empty ComponentDetails), or a raw JSON string.
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

    if data is None:
        # Real WIZ exports emit `details: "null"` for empty/template dialogues.
        # Treat as zero-node canvas; WIZ006 surfaces this state to the user.
        return ComponentDetails(flow_nodes={}, root_uuids=())
    if not isinstance(data, dict):
        raise ParseError(
            f"BizSpeechComponent.details parsed to {type(data).__name__}, expected object or null"
        )
    # Detect format: legacy uses {"list": [...]}, real WIZ uses {uuid: {...}}
    if _is_legacy_details(data):
        # Legacy / fixture format: flat list at top level.
        top_level_entries = data["list"]
    else:
        # Real WIZ export format: dict keyed by node UUID; flow nodes are nested
        # inside canvas.component.props.list of each envelope.
        top_level_entries = []
        for _node_key, envelope in data.items():
            if not isinstance(envelope, dict):
                continue
            props = (
                envelope.get("canvas", {})
                .get("component", {})
                .get("props", {})
            )
            top_level_entries.extend(props.get("list", []))

    nodes: dict[UUID, FlowNode] = {}
    roots: list[UUID] = []
    seen_uuids: set[UUID] = set()

    def _process_entries(entry_list: list[dict[str, Any]]) -> None:
        for entry in entry_list:
            if not isinstance(entry, dict):
                continue
            uuid = _parse_uuid(_require(entry, "uuid", "FlowNode"), "FlowNode.uuid")
            if uuid in seen_uuids:
                continue
            seen_uuids.add(uuid)
            parent_raw = entry.get("parentId")
            # Real WIZ uses "" for no-parent; legacy uses null/None.
            if parent_raw is None or parent_raw == "":
                parent_uuid = None
            else:
                parent_uuid = _parse_uuid(parent_raw, "FlowNode.parentId")
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
            # Process nested children (real WIZ format embeds them inline)
            children = entry.get("children", [])
            if children:
                _process_entries(children)

    _process_entries(top_level_entries)
    return ComponentDetails(flow_nodes=nodes, root_uuids=tuple(roots))
