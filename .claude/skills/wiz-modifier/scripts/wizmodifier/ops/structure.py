"""Structure ops: add BSC keys, populate the details payload, add a component."""

from __future__ import annotations

import json

from wizbuilder.noderender import EdgeSpec, NodeSpec, render_component_nodes

from wizmodifier import codec
from wizmodifier.io import InputBundle
from wizmodifier.ops._bsc import get_components, require_component, set_components

# The 6 keys wiz-builder adds to every BSC entry (canvases.py:119-124).
# NOTE: nluConf and outboundPorts overlap with _SECONDARY_STRIP_KEYS. add-bsc-keys is an
# opt-in op that intentionally re-adds those keys when explicit template parity is needed.
DEFAULT_BSC_KEYS = {
    "inboundPorts": "[]",
    "outboundPorts": "[]",
    "routes": "[]",
    "nluConf": "{}",
    "sourceUuid": "",
    # topFloorDetails is a JSON-encoded LIST (wiz-checker schema fields.md); WIZ import
    # parses it as an array, so "{}" => "expect [, actual {" once a component has nodes.
    "topFloorDetails": "[]",
}

# Keys from the Empty+Dialogue template that must not appear on secondary components.
# Confirmed by diffing real WIZ.AI multi-component exports vs T8 output:
# - createBy/createTime/language: template server metadata, absent from all real secondary BSCs
# - nluConf/outboundPorts/updateBy: only on real component[0], not component[1+]
_SECONDARY_STRIP_KEYS = frozenset({
    "createBy", "createTime", "language",
    "nluConf", "outboundPorts", "updateBy",
})

# System branch names used to resolve branch_intent_ids from SpeechIntent.
_SYSTEM_BRANCH_NAMES = {"Positive", "Negative", "Reject", "Unclassified", "No answer"}

# Default node_language code: "3" = Bahasa Indonesia (IDN).
# The modifier operates on an existing export and has no manifest language field.
# We default to IDN ("3") because it is the only validated language code in this MVP.
# If the export's BizSpeechComponent carries a "language" field with a known mapping,
# that value is preferred; otherwise "3" is used.
_LANGUAGE_CODE_MAP = {0: "3"}  # WIZ language int 0 → node_language "3" (IDN)
_DEFAULT_NODE_LANGUAGE = "3"


def _resolve_context(bundle: InputBundle) -> tuple[int, dict[str, int], list[str], str]:
    """Extract speech_id, branch_intent_ids, kb_ids, and node_language from bundle.data.

    Returns (speech_id, branch_intent_ids, kb_ids, node_language).
    Mirrors the lookups in wiz-builder's canvases.py:apply_canvases.
    """
    # speech_id from first component (same as canvases.py approach)
    bsc_raw = bundle.data.get("BizSpeechComponent", "[]")
    bsc = json.loads(bsc_raw) if isinstance(bsc_raw, str) else bsc_raw
    speech_id: int = bsc[0].get("speechId", 0) if bsc else 0

    # branch_intent_ids from SpeechIntent
    speech_intents_raw = bundle.data.get("SpeechIntent", "[]")
    speech_intents = (
        json.loads(speech_intents_raw)
        if isinstance(speech_intents_raw, str)
        else speech_intents_raw
    )
    branch_intent_ids: dict[str, int] = {
        i["intentName"]: i["intentId"]
        for i in speech_intents
        if i.get("intentName") in _SYSTEM_BRANCH_NAMES
    }

    # kb_ids from BizKnowledgeInfo
    biz_kb_raw = bundle.data.get("BizKnowledgeInfo", "[]")
    biz_kb = json.loads(biz_kb_raw) if isinstance(biz_kb_raw, str) else biz_kb_raw
    kb_ids: list[str] = [str(k["knowledgeId"]) for k in biz_kb]

    # node_language: try to read from existing component[0]; default to IDN "3"
    if bsc:
        lang_int = bsc[0].get("language", 0)
        node_language = _LANGUAGE_CODE_MAP.get(lang_int, _DEFAULT_NODE_LANGUAGE)
    else:
        node_language = _DEFAULT_NODE_LANGUAGE

    return speech_id, branch_intent_ids, kb_ids, node_language


def _render_nodes(
    params: dict,
    bundle: InputBundle,
    canvas_index: int,
    comp_uuid: str,
    minter,
):
    """Build NodeSpec/EdgeSpec lists from params and call render_component_nodes.

    params["nodes"] is a list of {id, prompt}.
    params.get("edges") is an optional list of {from, branch, to} (from/to map to src/dst).

    Returns a RenderedNodes instance.
    """
    node_specs = [NodeSpec(id=n["id"], prompt=n["prompt"]) for n in params["nodes"]]
    raw_edges = params.get("edges") or []
    edge_specs = [EdgeSpec(src=e["from"], branch=e["branch"], dst=e["to"]) for e in raw_edges]

    speech_id, branch_intent_ids, kb_ids, node_language = _resolve_context(bundle)

    return render_component_nodes(
        node_specs,
        edge_specs,
        canvas_index=canvas_index,
        comp_uuid=comp_uuid,
        speech_id=speech_id,
        branch_intent_ids=branch_intent_ids,
        kb_ids=kb_ids,
        node_language=node_language,
        minter=minter,
    )


def _append_sentence_cut_speech(bundle: InputBundle, new_rows: list[dict]) -> None:
    """Decode SentenceCutSpeech, extend with new_rows, re-encode."""
    raw = bundle.data.get("SentenceCutSpeech", "[]")
    existing = json.loads(raw) if isinstance(raw, str) else list(raw)
    existing.extend(new_rows)
    bundle.data["SentenceCutSpeech"] = codec.encode(existing)


def add_bsc_keys(bundle: InputBundle, params: dict, minter) -> None:
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    keys = params.get("keys") or DEFAULT_BSC_KEYS
    comp.update(keys)
    set_components(bundle, comps)


def populate_details(bundle: InputBundle, params: dict, minter) -> None:
    """Populate details/routes/inboundPorts on an existing component using real node shape.

    params:
        component: int — index of the target BizSpeechComponent
        nodes: list[{id, prompt}] — node specs
        edges: list[{from, branch, to}] — optional edge specs (default [])

    Appends SentenceCutSpeech rows to bundle.data["SentenceCutSpeech"].
    """
    comps = get_components(bundle)
    index = params["component"]
    comp = require_component(comps, index)
    comp_uuid = comp.get("componentUuid", "")

    r = _render_nodes(params, bundle, canvas_index=index, comp_uuid=comp_uuid, minter=minter)

    comp["details"] = json.dumps(r.details, ensure_ascii=False, separators=(",", ":"))
    comp["routes"] = json.dumps(r.routes, ensure_ascii=False, separators=(",", ":"))
    comp["inboundPorts"] = json.dumps(r.inbound_ports, ensure_ascii=False, separators=(",", ":"))

    set_components(bundle, comps)
    _append_sentence_cut_speech(bundle, r.sentence_cut_speech)


def add_component(bundle: InputBundle, params: dict, minter) -> None:
    """Append a new BizSpeechComponent, cloning the first entry's shared keys.

    If params has a 'nodes' list (each {id, prompt}), the details/routes/inboundPorts
    are populated via render_component_nodes; otherwise details is the literal string
    "null" (empty-canvas convention).

    Optional params["edges"] list of {from, branch, to} wires node connections.
    Appends SentenceCutSpeech rows to bundle.data when nodes are provided.
    """
    comps = get_components(bundle)
    base = comps[0] if comps else {}
    index = len(comps)
    nodes = params.get("nodes")

    new_comp = dict(base)
    if index > 0:
        for key in _SECONDARY_STRIP_KEYS:
            new_comp.pop(key, None)
    new_comp["componentUuid"] = str(minter.uuid(f"modifier-component:{index}"))
    new_comp["name"] = params["name"]
    new_comp["id"] = minter.int_id(f"modifier-component-id:{index}")
    new_comp["parentUuid"] = "0"
    new_comp["sortIndex"] = index + 1

    if nodes:
        comp_uuid = new_comp["componentUuid"]
        # Temporarily append so _resolve_context can read speechId from comps[0]
        comps.append(new_comp)
        set_components(bundle, comps)

        r = _render_nodes(params, bundle, canvas_index=index, comp_uuid=comp_uuid, minter=minter)

        # Re-read after set_components mutated the bundle
        comps = get_components(bundle)
        new_comp = comps[-1]
        new_comp["details"] = json.dumps(r.details, ensure_ascii=False, separators=(",", ":"))
        new_comp["routes"] = json.dumps(r.routes, ensure_ascii=False, separators=(",", ":"))
        new_comp["inboundPorts"] = json.dumps(
            r.inbound_ports, ensure_ascii=False, separators=(",", ":")
        )
        set_components(bundle, comps)
        _append_sentence_cut_speech(bundle, r.sentence_cut_speech)
    else:
        new_comp["details"] = "null"
        comps.append(new_comp)
        set_components(bundle, comps)
