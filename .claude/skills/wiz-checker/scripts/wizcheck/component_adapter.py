"""Adapter: WIZ component-library export (componentImportAndExportDTOS envelope)
-> a full-export-shaped dict the existing parser/checks consume unchanged.

A component export is a single reusable component (or a few) exported from the
WIZ Dialogue/Component Library. Its shape differs from the full speech*.json:
DTO-wrapped, decoded details/routes, snake_case sentence-cut fields, trimmed
intent/variable rows. This module maps it back to the full-export shape.
"""
from __future__ import annotations

import copy
import json
from typing import Any

# Bot/scope checks that are structurally false-positive for a lone component
# (it legitimately references sibling components / KBs / vars defined elsewhere
# in its parent bot). Suppressed when validating a component export.
BOT_SCOPE_CODES = frozenset({"WIZ104", "WIZ110", "WIZ202", "WIZ303", "WIZ401", "WIZ402"})

_EMPTY_DEFAULTS = ([], {}, "", None)


def _prune_added_empty_keys(regen_scd: dict, base_scd: dict) -> None:
    """Drop regenerated speechComponentDTO keys that the base component did not
    have AND whose value is an empty default — so a modify round-trip does not
    inject keys (e.g. topFloorDetails:[]) the source never carried."""
    base_keys = set(base_scd) if isinstance(base_scd, dict) else set()
    for k in [k for k in regen_scd if k not in base_keys and regen_scd[k] in _EMPTY_DEFAULTS]:
        del regen_scd[k]


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


def _adapt_variable(dto: dict, comp: dict) -> dict:
    # Component-export variables lack 'speechId' and 'templateCode' fields;
    # add them from component (same pattern as sentence_cut adaptation).
    out = dict(dto)
    out.setdefault("branch", comp.get("branch", "dev"))
    out.setdefault("speechId", comp.get("speechId"))
    out.setdefault("templateCode", comp.get("templateCode"))
    return out


def component_export_to_full(raw: dict) -> dict:
    """Build a full-export-shaped dict from a component-export envelope."""
    entries = raw.get("componentImportAndExportDTOS") or []
    components: list[dict] = []
    sentence_cuts: list[dict] = []
    first_comp = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        comp = _adapt_component(entry)
        if comp is None:
            continue
        if first_comp is None:
            first_comp = comp
        components.append(comp)
        for row in entry.get("sentenceCutDTOList") or []:
            if isinstance(row, dict):
                sentence_cuts.append(_adapt_sentence_cut(row, comp))

    intents = [_adapt_intent(i) for i in (raw.get("speechIntentDTO") or [])
               if isinstance(i, dict)]
    # Use first component's branch for variables; all components share the intent/variable defs.
    default_comp = first_comp or {}
    variables = [_adapt_variable(v, default_comp) for v in (raw.get("speechVariableDTO") or [])
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


def full_to_component_export(
    full: dict, *, name: str | None = None, base: dict | None = None
) -> dict:
    """Inverse of component_export_to_full: full-export dict -> component-export DTO.

    Accepts a builder-produced full-export dict (sections may be escaped-JSON
    strings or already-decoded). Emits the componentImportAndExportDTOS envelope.

    When ``base`` is given (the original envelope the modifier loaded), the
    modeled sections are regenerated from ``full`` and overlaid onto a deep copy
    of ``base``; every other field of ``base`` (passthrough entity/function/tag
    lists, per-entry asrSceneEntityList/speechId/templateCode/enterpriseId, and
    ``name``) is preserved verbatim. Components are matched by componentUuid;
    a component in ``full`` but not ``base`` is appended, one in ``base`` but not
    ``full`` is dropped.
    """
    comps = _dec(full.get("BizSpeechComponent")) or []
    scs = _dec(full.get("SentenceCutSpeech")) or []
    intents = _dec(full.get("SpeechIntent")) or []
    variables = _dec(full.get("SpeechVariable")) or []
    if not isinstance(comps, list):
        comps = []

    cuts_by_comp: dict[str, list] = {}
    if isinstance(scs, list):
        for row in scs:
            if isinstance(row, dict):
                cuts_by_comp.setdefault(row.get("componentUuid"), []).append(row)

    intent_dtos = [_to_intent_dto(i) for i in intents if isinstance(i, dict)]
    var_dtos = [_to_variable_dto(v) for v in variables if isinstance(v, dict)]

    if base is not None:
        return _splice_component_export(
            base, comps, cuts_by_comp, intent_dtos, var_dtos, name
        )

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
        "speechIntentDTO": intent_dtos,
        "speechVariableDTO": var_dtos,
        "speechEntiEntityList": [],
        "speechEntityData": [],
        "speechFunctionDTO": [],
        "tagDTOList": [],
    }


def _new_component_entry(comp: dict, cuts_by_comp: dict) -> dict:
    cu = comp.get("componentUuid")
    return {
        "componentName": comp.get("name", ""),
        "componentUuid": cu,
        "speechId": comp.get("speechId"),
        "templateCode": comp.get("templateCode"),
        "enterpriseId": comp.get("enterpriseId", 0),
        "asrSceneEntityList": [],
        "speechComponentDTO": _to_speech_component_dto(comp),
        "sentenceCutDTOList": [_to_sentence_cut_dto(r) for r in cuts_by_comp.get(cu, [])],
    }


def _splice_component_export(base, comps, cuts_by_comp, intent_dtos, var_dtos, name):
    out = copy.deepcopy(base)
    comp_by_uuid = {c.get("componentUuid"): c for c in comps if isinstance(c, dict)}
    base_entries = out.get("componentImportAndExportDTOS") or []
    new_entries = []
    for entry in base_entries:
        cu = entry.get("componentUuid")
        comp = comp_by_uuid.pop(cu, None)
        if comp is None:
            continue  # component deleted by an op -> drop its entry
        # Read base speechComponentDTO before overwriting, so we can prune
        # any spurious empty keys that flush injected.
        base_scd = entry.get("speechComponentDTO") or {}
        regen = _to_speech_component_dto(comp)
        _prune_added_empty_keys(regen, base_scd)
        entry["speechComponentDTO"] = regen
        entry["sentenceCutDTOList"] = [
            _to_sentence_cut_dto(r) for r in cuts_by_comp.get(cu, [])
        ]
        entry["componentName"] = comp.get("name", entry.get("componentName", ""))
        new_entries.append(entry)
    # components added by an op (uuid absent from base) -> append fresh entries
    for _cu, comp in comp_by_uuid.items():
        new_entries.append(_new_component_entry(comp, cuts_by_comp))
    out["componentImportAndExportDTOS"] = new_entries
    out["speechIntentDTO"] = intent_dtos
    out["speechVariableDTO"] = var_dtos
    if name is not None:
        out["name"] = name
    return out
