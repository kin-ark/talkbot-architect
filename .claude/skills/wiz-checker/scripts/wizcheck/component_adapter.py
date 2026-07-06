"""Adapter: WIZ component-library export (componentImportAndExportDTOS envelope)
-> a full-export-shaped dict the existing parser/checks consume unchanged.

A component export is a single reusable component (or a few) exported from the
WIZ Dialogue/Component Library. Its shape differs from the full speech*.json:
DTO-wrapped, decoded details/routes, snake_case sentence-cut fields, trimmed
intent/variable rows. This module maps it back to the full-export shape.
"""
from __future__ import annotations

import json
from typing import Any

# Bot/scope checks that are structurally false-positive for a lone component
# (it legitimately references sibling components / KBs / vars defined elsewhere
# in its parent bot). Suppressed when validating a component export.
BOT_SCOPE_CODES = frozenset({"WIZ104", "WIZ110", "WIZ202", "WIZ303"})


def is_component_export(raw: Any) -> bool:
    """True if `raw` is a WIZ component-library export envelope."""
    return isinstance(raw, dict) and "componentImportAndExportDTOS" in raw


def _adapt_component(dto_entry: dict) -> dict | None:
    scd = dto_entry.get("speechComponentDTO")
    if not isinstance(scd, dict):
        return None
    comp = dict(scd)  # copy; details/routes/inboundPorts stay decoded
    # WIZ005 needs non-zero createTime + updateTime; DTO carries updateTime only.
    update_time = comp.get("updateTime") or 1
    comp["updateTime"] = update_time
    comp.setdefault("createTime", update_time)
    return comp


def _adapt_sentence_cut(row: dict, comp: dict) -> dict:
    # Remap DTO fields to full-export shape; unknown DTO fields are intentionally dropped.
    return {
        "id": row.get("id"),
        "componentUuid": row.get("componentUuid"),
        "sentenceText": row.get("sentence_text", ""),
        "senRecName": row.get("sen_rec_name", ""),
        "sentenceTextUrl": row.get("sentence_text_url", ""),
        "speechRecCutId": row.get("speech_rec_cut_id", ""),
        "sentenceCutId": row.get("sentenceCutId"),
        "showType": row.get("showType", 0),
        "sortIndex": row.get("sortIndex", 0),
        "type": row.get("type", "record"),
        "isDelete": row.get("is_delete", 0),
        "branch": comp.get("branch", "dev"),
        "speechId": comp.get("speechId"),
    }


def _adapt_intent(dto: dict) -> dict:
    out = dict(dto)
    out.setdefault("isDelete", 0)
    return out


def component_export_to_full(raw: dict) -> dict:
    """Build a full-export-shaped dict from a component-export envelope."""
    entries = raw.get("componentImportAndExportDTOS") or []
    components: list[dict] = []
    sentence_cuts: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        comp = _adapt_component(entry)
        if comp is None:
            continue
        components.append(comp)
        for row in entry.get("sentenceCutDTOList") or []:
            if isinstance(row, dict):
                sentence_cuts.append(_adapt_sentence_cut(row, comp))

    intents = [_adapt_intent(i) for i in (raw.get("speechIntentDTO") or [])
               if isinstance(i, dict)]
    variables = [dict(v) for v in (raw.get("speechVariableDTO") or [])
                 if isinstance(v, dict)]

    return {
        "BizSpeechComponent": components,
        "SentenceCutSpeech": sentence_cuts,
        "SpeechIntent": intents,
        "SpeechVariable": variables,
        "SpeechAudio": [],
        "BizNodeHotWords": "[]",
    }


def _dec(value: object) -> object:
    """json.loads a string field; pass objects/None through."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


def _unbracket(value: object, sep: str) -> list:
    """Inverse of wizbuilder _bracket_join: '[a<sep>b]' -> ['a','b']. Tolerant of
    already-a-list input and empty '[]'."""
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    s = value.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    return [p for p in s.split(sep) if p != ""] if s else []


_SCD_DECODE_FIELDS = ("details", "routes", "inboundPorts", "outboundPorts",
                      "topFloorDetails", "nluConf")
_SCD_DROP_FIELDS = ("createTime", "createBy", "language")


def _to_speech_component_dto(comp: dict) -> dict:
    scd = dict(comp)
    for f in _SCD_DECODE_FIELDS:
        if f in scd:
            scd[f] = _dec(scd[f])
    for f in _SCD_DROP_FIELDS:
        scd.pop(f, None)
    scd.setdefault("version", "4")
    return scd


def _to_sentence_cut_dto(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "componentUuid": row.get("componentUuid"),
        "sentence_text": row.get("sentenceText", ""),
        "sen_rec_name": row.get("senRecName", ""),
        "sentence_text_url": row.get("sentenceTextUrl", ""),
        "speech_rec_cut_id": row.get("speechRecCutId", ""),
        "is_delete": row.get("isDelete", 0),
        "sentenceCutId": row.get("sentenceCutId"),
        "showType": row.get("showType", 0),
        "sortIndex": row.get("sortIndex", 0),
        "type": row.get("type", "record"),
    }


def _to_intent_dto(row: dict) -> dict:
    return {
        "intentId": row.get("intentId"),
        "intentName": row.get("intentName"),
        "isInit": row.get("isInit", 1),
        "language": row.get("language", ""),
        "keyWordInIntent": _unbracket(row.get("keyWordInIntent"), ","),
        "userResponseInIntent": _unbracket(row.get("userResponseInIntent"), ";"),
        "preExclusiveKeyword": row.get("preExclusiveKeyword", []),
        "preInclusiveKeyword": row.get("preInclusiveKeyword", []),
    }


_VAR_KEEP = ("beInit", "id", "name", "textType", "type", "userId", "variableSource")


def _to_variable_dto(row: dict) -> dict:
    out = {k: row[k] for k in _VAR_KEEP if k in row}
    if "remark" in row:
        out["remark"] = row["remark"]
    return out


def full_to_component_export(full: dict, *, name: str | None = None) -> dict:
    """Inverse of component_export_to_full: full-export dict -> component-export DTO.

    Accepts a builder-produced full-export dict (sections may be escaped-JSON
    strings or already-decoded).  Emits the componentImportAndExportDTOS envelope.
    """
    comps = _dec(full.get("BizSpeechComponent")) or []
    scs = _dec(full.get("SentenceCutSpeech")) or []
    intents = _dec(full.get("SpeechIntent")) or []
    variables = _dec(full.get("SpeechVariable")) or []
    if not isinstance(comps, list):
        comps = []

    # group sentence-cuts by componentUuid
    cuts_by_comp: dict[str, list] = {}
    if isinstance(scs, list):
        for row in scs:
            if isinstance(row, dict):
                cuts_by_comp.setdefault(row.get("componentUuid"), []).append(row)

    entries = []
    for comp in comps:
        if not isinstance(comp, dict):
            continue
        cu = comp.get("componentUuid")
        entries.append({
            "componentName": comp.get("name", ""),
            "componentUuid": cu,
            "speechId": comp.get("speechId"),
            "templateCode": comp.get("templateCode"),
            "enterpriseId": comp.get("enterpriseId", 0),
            "asrSceneEntityList": [],
            "speechComponentDTO": _to_speech_component_dto(comp),
            "sentenceCutDTOList": [_to_sentence_cut_dto(r) for r in cuts_by_comp.get(cu, [])],
        })

    return {
        "name": name or (entries[0]["componentName"] if entries else ""),
        "componentImportAndExportDTOS": entries,
        "speechIntentDTO": [_to_intent_dto(i) for i in intents if isinstance(i, dict)],
        "speechVariableDTO": [_to_variable_dto(v) for v in variables if isinstance(v, dict)],
        "speechEntiEntityList": [],
        "speechEntityData": [],
        "speechFunctionDTO": [],
        "tagDTOList": [],
    }
