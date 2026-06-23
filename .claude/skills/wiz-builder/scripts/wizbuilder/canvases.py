"""apply_canvases: replace the empty template canvas with manifest-defined canvases.

Uses render_component_nodes (noderender.py) to produce the real WIZ.AI node shape
validated against the importer in Phase 1. Each canvas becomes one BizSpeechComponent
entry with fully-wired details, routes, inboundPorts, and SentenceCutSpeech rows.
"""

from __future__ import annotations

import json
from typing import Any

from wizbuilder.ids import IdMinter
from wizbuilder.manifest import Canvas, Manifest
from wizbuilder.noderender import EdgeSpec, NodeSpec, render_component_nodes

# Keys present only on component[0] in real WIZ.AI exports.
# Secondary components (index > 0) must NOT carry these keys.
_SECONDARY_STRIP_KEYS = frozenset({
    "createBy",
    "createTime",
    "language",
    "nluConf",
    "outboundPorts",
    "updateBy",
})

# Map manifest language codes to WIZ.AI node_language strings.
# "3" is confirmed for IDN from reference exports.  All sampled exports (including
# an ENG-intent bot) also carry languageItem="3" in BizSpeechScene, so "3" is a
# safe placeholder for the remaining documented languages until per-language reference
# exports are decoded.
_LANGUAGE_MAP = {
    "IDN": "3",
    "ENG": "3",
    # TODO(lang-codes): verify ZHO/THA (and ENG) numeric codes from non-IDN reference exports — "3" is an empirical placeholder and may mislabel NLU/TTS routing for these languages.
    "ZHO": "3",
    "THA": "3",
}


def apply_canvases(
    template: dict[str, Any],
    manifest: Manifest,
    minter: IdMinter,
) -> dict[str, Any]:
    """Replace the template's BizSpeechComponent list with manifest canvases."""
    raw = template.get("BizSpeechComponent")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            "apply_canvases requires template['BizSpeechComponent'] to be a non-empty JSON string"
        )
    template_bsc = json.loads(raw)
    base = template_bsc[0] if template_bsc else {}
    speech_id = base.get("speechId", 0)

    # Resolve branch_intent_ids from template SpeechIntent
    _system_branch_names = {"Positive", "Negative", "Reject", "Unclassified", "No answer"}
    speech_intents_raw = template.get("SpeechIntent", "[]")
    speech_intents = (
        json.loads(speech_intents_raw)
        if isinstance(speech_intents_raw, str)
        else speech_intents_raw
    )
    branch_intent_ids: dict[str, int] = {
        i["intentName"]: i["intentId"]
        for i in speech_intents
        if i.get("intentName") in _system_branch_names
    }

    # Resolve kb_ids from template BizKnowledgeInfo
    biz_kb_raw = template.get("BizKnowledgeInfo", "[]")
    biz_kb = json.loads(biz_kb_raw) if isinstance(biz_kb_raw, str) else biz_kb_raw
    kb_ids: list[str] = [str(k["knowledgeId"]) for k in biz_kb]

    # Resolve node_language from manifest.language
    node_language = _LANGUAGE_MAP.get(manifest.language)
    if node_language is None:
        raise ValueError(
            f"Unsupported manifest language {manifest.language!r}. "
            f"Only {sorted(_LANGUAGE_MAP)} are supported in this MVP."
        )

    all_sentence_cut_rows: list[dict] = []
    new_components = []
    for ci, canvas in enumerate(manifest.canvases):
        comp, scs_rows = _build_component(
            canvas=canvas,
            canvas_index=ci,
            manifest=manifest,
            minter=minter,
            base=base,
            speech_id=speech_id,
            branch_intent_ids=branch_intent_ids,
            kb_ids=kb_ids,
            node_language=node_language,
        )
        new_components.append(comp)
        all_sentence_cut_rows.extend(scs_rows)

    template["BizSpeechComponent"] = json.dumps(
        new_components, ensure_ascii=False, separators=(",", ":")
    )
    template["SentenceCutSpeech"] = json.dumps(
        all_sentence_cut_rows, ensure_ascii=False, separators=(",", ":")
    )
    return template


def _build_component(
    canvas: Canvas,
    canvas_index: int,
    manifest: Manifest,
    minter: IdMinter,
    base: dict[str, Any],
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
) -> tuple[dict[str, Any], list[dict]]:
    """Build a single BizSpeechComponent entry using render_component_nodes.

    Returns (component_dict, sentence_cut_speech_rows).
    """
    canvas_uuid = str(minter.uuid(f"component:{canvas_index}"))

    node_specs = [NodeSpec(id=n.id, prompt=n.prompt) for n in canvas.nodes]
    edge_specs = [EdgeSpec(src=e.src, branch=e.branch, dst=e.dst) for e in canvas.edges]

    r = render_component_nodes(
        node_specs,
        edge_specs,
        canvas_index=canvas_index,
        comp_uuid=canvas_uuid,
        speech_id=speech_id,
        branch_intent_ids=branch_intent_ids,
        kb_ids=kb_ids,
        node_language=node_language,
        minter=minter,
    )

    entry = {
        "componentUuid": canvas_uuid,
        "name": canvas.name,
        "branch": manifest.branch,
        "category": base.get("category", 1),
        "type": base.get("type", 1),
        "language": base.get("language", 0),
        "editStatus": base.get("editStatus", 1),
        "useStatus": base.get("useStatus", 1),
        "parentUuid": "0",
        "sortIndex": canvas_index + 1,
        "speechId": speech_id,
        "templateCode": base.get("templateCode", ""),
        "createBy": base.get("createBy", 0),
        "updateBy": base.get("updateBy", 0),
        "createTime": base.get("createTime", 0),
        "updateTime": base.get("updateTime", 0),
        "id": minter.int_id(f"component-id:{canvas_index}"),
        "inboundPorts": json.dumps(r.inbound_ports, ensure_ascii=False, separators=(",", ":")),
        "outboundPorts": "[]",
        "routes": json.dumps(r.routes, ensure_ascii=False, separators=(",", ":")),
        "nluConf": "{}",
        "sourceUuid": "",
        # topFloorDetails is a JSON-encoded LIST (wiz-checker schema fields.md);
        # WIZ import parses it as an array, so "{}" => "expect [, actual {" once a
        # component carries real nodes. Empty list is valid for both empty + populated.
        "topFloorDetails": "[]",
        "details": json.dumps(r.details, ensure_ascii=False, separators=(",", ":")),
    }

    if canvas_index > 0:
        for key in _SECONDARY_STRIP_KEYS:
            entry.pop(key, None)

    return entry, r.sentence_cut_speech
