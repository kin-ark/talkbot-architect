"""Adapter: WIZ component-library export (componentImportAndExportDTOS envelope)
-> a full-export-shaped dict the existing parser/checks consume unchanged.

A component export is a single reusable component (or a few) exported from the
WIZ Dialogue/Component Library. Its shape differs from the full speech*.json:
DTO-wrapped, decoded details/routes, snake_case sentence-cut fields, trimmed
intent/variable rows. This module maps it back to the full-export shape.
"""
from __future__ import annotations

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
        "isDelete": 0,
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
