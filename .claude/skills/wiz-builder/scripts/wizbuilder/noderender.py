"""wizbuilder.noderender — pure serializer for a single WIZ.AI canvas Talk Node.

Ported from the validated prototype scripts/proto_graph_emit.py::build_node.
Produces the exact node shape required by the WIZ.AI importer (reverse-engineered
and validated in Phase 1; see docs/node-serialization-spec.md).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Public dataclasses (consumed by Task 2+ callers — do NOT rename fields)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeSpec:
    id: str
    prompt: str
    type: str = "talk"
    config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EdgeSpec:
    src: str     # source node id (not uuid — logical id from NodeSpec)
    branch: str  # branch name, e.g. "Unclassified"
    dst: str     # destination node id


@dataclass(frozen=True)
class RenderedNodes:
    details: dict         # {node_uuid: node_obj}
    routes: dict          # {node_uuid: {port_uuid: edge_obj} | {}}
    inbound_ports: list   # [{name, type, uuid, is_default}]
    sentence_cut_speech: list  # rows
    top_floor_details: list   # one row per exit-family node (type 2 only; type 13 excluded)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Branches in the canonical WIZ.AI order; (name, checked) tuples.
_BRANCH = [
    ("Positive", True),
    ("Negative", True),
    ("Reject", False),
    ("Unclassified", True),
    ("No answer", False),
]
_CHECKED = [name for name, checked in _BRANCH if checked]


def _fo(x: float, w: int) -> dict:
    """Return a foreignObject geometry dict used for port attrs."""
    return {"fo": {"x": x, "width": w, "y": -30, "magnet": "true", "height": 24}}


def _wide_int(seed: str) -> int:
    """Return a wide positive int (~2e18 range) derived deterministically from seed.

    int_id() from IdMinter is capped at int32; sentenceCutId needs a wider value
    to match WIZ.AI's native 64-bit IDs.
    """
    raw = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big")
    return (raw & 0x7FFFFFFFFFFFFFFF) or 1


_PORT_MARKUP = [
    {
        "children": [
            {
                "ns": "http://www.w3.org/1999/xhtml",
                "children": [
                    {
                        "style": {"width": "100%", "height": "100%"},
                        "selector": "foContent",
                        "tagName": "div",
                    }
                ],
                "style": {"background": "transparent", "width": "100%", "height": "100%"},
                "selector": "foBody",
                "tagName": "body",
                "attrs": {"xmlns": "http://www.w3.org/1999/xhtml"},
            }
        ],
        "selector": "fo",
        "tagName": "foreignObject",
    }
]

# Canonical operator tokens as emitted by the WIZ.AI UI (confirmed from real exports).
# Friendly authoring tokens (left) map to the platform's canonical strings (right).
_WIZ_OPERATOR: dict[str, str] = {
    ">": ">",
    ">=": ">=",
    "<": "<",
    "<=": "<=",
    "=": "=",
    "!=": "!=",
    "In": "In",
    "NotIn": "Not in",
    "IsNull": "Null",
    "NotNull": "Not null",
    "Contains": "Contain",
}

_TYPE_INT = {
    "talk": 1, "exit": 2, "goto": 4, "conditional": 7, "goto_kb": 8, "assign": 10, "nested": 11,
    "transfer": 13, "exit_port": 4, "goto_mr": 9,
}
_TYPE_NODE_NAME = {
    "talk": "Talk Node",
    "conditional": "Conditional Judgment Node",
    "assign": "Variable Assignment Node",
    "nested": "Nested Component Node",
}


# ---------------------------------------------------------------------------
# Per-type node builders
# ---------------------------------------------------------------------------


def _build_scs_row(
    *,
    comp_uuid: str,
    node_uuid: str,
    reccut_uuid: str,
    minter: Any,
    canvas_index: int,
    nid_str: str,
    sort_index: int,
    speech_id: int,
    text: str,
) -> dict:
    """Build a SentenceCutSpeech row — shared by talk, exit, and transfer builders."""
    return {
        "branch": "dev",
        "componentUuid": comp_uuid,
        "id": node_uuid,
        "isDelete": 0,
        "senRecName": "",
        "sentenceCutId": _wide_int(
            f"{getattr(minter, 'manifest_hash', '')}:scid:{canvas_index}:{nid_str}"
        ),
        "sentenceText": text,
        "sentenceTextUrl": "",
        "showType": 0,
        "sortIndex": sort_index,
        "speechId": speech_id,
        "speechRecCutId": reccut_uuid,
        "type": "record",
    }


def _build_talk_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,  # unused by Talk; accepted for uniform dispatch
    var_source_by_name: dict[str, int] | None = None,  # unused; accepted for uniform dispatch
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, dict]:
    """Build one Talk-node ``node_obj`` and ``scs_row``.

    Returns (node_obj, scs_row) — a (details-entry, SentenceCutSpeech-row) pair.
    """
    nid_str = spec.id
    ci = canvas_index

    # --- canvas.ports.items (one per checked branch) ---
    items = [
        {"name": b, "id": port_uuids[b], "attrs": _fo(-37.67, 70), "group": "out"}
        for b in _CHECKED
    ]

    canvas = {
        "view": "react-shape-view",
        "component": {"props": {"text": "Talk Node", "list": [], "type": 1}},
        "size": {"width": 346, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -461.97, "y": 157.23},
        "ports": {
            "groups": {
                "in": {"position": {"name": "top"}, "attrs": _fo(-30, 140)},
                "out": {
                    "position": {"left": 200, "name": "bottom"},
                    "attrs": {"fo": {"magnet": "true", "height": 24}},
                },
            },
            "items": items,
        },
        "portMarkup": _PORT_MARKUP,
        "zIndex": 1,
    }

    # --- all_client_intent (5 system branches, checked ones carry port uuid) ---
    aci = []
    for b_name, b_checked in _BRANCH:
        row: dict = {
            "intents": [{"intentId": str(branch_intent_ids[b_name])}],
            "name": b_name,
            "match": False,
            "checked": b_checked,
            "language": node_language,
            "threshold": "",
        }
        if b_checked:
            row["id"] = port_uuids[b_name]
        aci.append(row)

    text = spec.prompt
    xml = (
        '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">'
        f'<wiz:express-as style="default">{text}</wiz:express-as></speak>'
    )

    data: dict = {
        "speakType": 1,
        "all_client_intent": aci,
        "node_language_item": node_language,
        "intention_judgment_time": 2,
        "type": 1,
        "repeat_script_type": 0,
        "hot_words_list": [],
        "dialog_list": [{"xml": xml, "html": f"<p>{text}</p>", "text": text}],
        "user_response_mode": "voice",
        "tag_list": [],
        "openChasingDedayTime": False,
        "openUserPauseDuration": False,
        "can_be_interrupted": 0,
        "id": node_uuid,
        "node_repetition": 0,
        "open_pause_duration": False,
        "selected": False,
        "openChasingDedayTim": False,
        "allow_jump_knowledges_switch": 0,
        "client_intent": _CHECKED,
        "intent_rollback_enable": False,
        "node_variables": [],
        "allow_jump_knowledges": list(kb_ids),
        "is_transfer": 0,
        "value_assignment": [],
        "global_unclassified_switch": 0,
        "list": [text],
        "is_default": is_default,
        "nodeLabelArr": [],
        "node_language": node_language,
        "agent_type": "SYSTEM",
        "tts_language": node_language,
        "intent_tag_def": {
            n: {"tag_list": [], "intent_code": ""}
            for n in ("No answer", "Reject", "Negative", "Positive", "Unclassified")
        },
        "open_talk_finish": False,
        "can_interrupt_percent": 0.8,
        "name": "Talk Node",
        "notices_info": [],
        "notice_send_type": 0,
        "position": {"x": -461.97, "y": 157.23},
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": "Talk Node",
        "type": 1,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [],
            "intents": [
                {"intentId": str(branch_intent_ids[b_name])} for b_name, _ in _BRANCH
            ],
            "variables": [],
            "serviceCall": [],
            "sentence_cut": [],
        },
    }

    # --- SentenceCutSpeech row ---
    scs_row: dict = _build_scs_row(
        comp_uuid=comp_uuid,
        node_uuid=node_uuid,
        reccut_uuid=reccut_uuid,
        minter=minter,
        canvas_index=ci,
        nid_str=nid_str,
        sort_index=sort_index,
        speech_id=speech_id,
        text=text,
    )

    return node_obj, scs_row


def _build_exit_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,  # unused; accepted for uniform dispatch
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, dict]:
    """Build one Exit-node (type 2) ``node_obj`` and ``scs_row``.

    Terminal: no ports.  Returns (node_obj, scs_row).
    """
    text = spec.prompt
    xml = (
        '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">'
        f'<wiz:express-as style="default">{text}</wiz:express-as></speak>'
    )

    canvas = {
        "view": "react-shape-view",
        "component": {
            "props": {
                "text": "Exit Node",
                "list": list(component_nav) if component_nav else [],
                "type": 2,
            }
        },
        "size": {"width": 169, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -370, "y": 390},
        "zIndex": 2,
    }

    data: dict = {
        "appoint_node_id": "",
        "speakType": 1,
        "hitKnowledgeRate": [],
        "intention_judgment_time": 2,
        "type": 2,
        "repeat_script_type": 0,
        "hot_words_list": [],
        "hangupRate": "0.0%",
        "exclusive_key_words": [],
        "dialog_list": [{"xml": xml, "html": f"<p>{text}</p>", "text": text}],
        "tag_list": [],
        "openUserPauseDuration": False,
        "can_be_interrupted": 0,
        "id": node_uuid,
        "node_repetition": 0,
        "open_pause_duration": False,
        "selected": False,
        "hitKnowledgeCountsRate": "0.0%",
        "multiple_appoint_id": "",
        "openChasingDedayTim": False,
        "allow_jump_knowledges_switch": 0,
        "allow_jump_knowledges": list(kb_ids),
        "is_transfer": 0,
        "appoint_knowledge_id": "",
        "list": [text],
        "is_default": is_default,
        "textareaList": [""],
        "nodeLabelArr": [],
        "node_language": node_language,
        "agent_type": "SYSTEM",
        "tts_language": node_language,
        "sms_id": "",
        "can_interrupt_percent": 0.8,
        "name": "Exit Node",
        "notices_info": [],
        "notice_send_type": 0,
        "position": {"x": -750.43, "y": 380.75},
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": "Exit Node",
        "type": 2,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [],
            "intents": [],
            "variables": [],
            "serviceCall": [],
            "sentence_cut": [],
        },
    }

    scs_row: dict = _build_scs_row(
        comp_uuid=comp_uuid,
        node_uuid=node_uuid,
        reccut_uuid=reccut_uuid,
        minter=minter,
        canvas_index=canvas_index,
        nid_str=spec.id,
        sort_index=sort_index,
        speech_id=speech_id,
        text=text,
    )

    return node_obj, scs_row


def _build_goto_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,  # unused; accepted for uniform dispatch
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, None]:
    """Build one goto_component node (type 4) ``node_obj``.

    Terminal: no ports, no SentenceCutSpeech row.  Returns (node_obj, None).
    The caller must supply resolved target info in spec.config:
      - config["target_uuid"]: pre-minted componentUuid of the target canvas
      - config["target_name"]: canonical canvas name (e.g. "2. Second Canvas")
    These are injected by canvases.py's name→uuid map before calling render_component_nodes,
    or by the modifier's structure.py which resolves against the existing export's components.

    Emits a topFloorDetails row (type 4) identical to the data dict (confirmed by fixture 25).
    """
    target_uuid: str = spec.config.get("target_uuid", "")
    target_name: str = spec.config.get("target_name", spec.config.get("target", ""))

    canvas = {
        "view": "react-shape-view",
        "component": {
            "props": {
                "text": "Exit Node",
                "list": list(component_nav) if component_nav else [],
                "type": 2,
            }
        },
        "size": {"width": 234, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -450, "y": 390},
        "zIndex": 2,
    }

    data: dict = {
        "appoint_node_id": target_uuid,
        "speakType": 1,
        "hitKnowledgeRate": [],
        "intention_judgment_time": 2,
        "type": 4,
        "repeat_script_type": 0,
        "hot_words_list": [],
        "specificComponentName": target_name,
        "hangupRate": "0.0%",
        "exclusive_key_words": [],
        "openUserPauseDuration": False,
        "can_be_interrupted": 0,
        "id": node_uuid,
        "node_repetition": 0,
        "open_pause_duration": False,
        "selected": False,
        "hitKnowledgeCountsRate": "0.0%",
        "multiple_appoint_id": "",
        "openChasingDedayTim": False,
        "allow_jump_knowledges_switch": 0,
        "allow_jump_knowledges": list(kb_ids),
        "is_transfer": 0,
        "appoint_knowledge_id": "",
        "is_default": is_default,
        "textareaList": [""],
        "nodeLabelArr": [],
        "node_language": node_language,
        "agent_type": "SYSTEM",
        "sms_id": "",
        "can_interrupt_percent": 80,
        "name": "Exit Node",
        "notices_info": [],
        "notice_send_type": 0,
        "position": {"x": -450, "y": 390},
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": "Exit Node",
        "type": 4,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [],
            "intents": [],
            "variables": [],
            "serviceCall": [],
            "sentence_cut": [],
        },
    }

    return node_obj, None


def _build_goto_mr_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,  # unused; accepted for uniform dispatch
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, None]:
    """Build one goto_mr node (type 9) ``node_obj``.

    Terminal: no ports, no SentenceCutSpeech row, no topFloorDetails row.
    Returns (node_obj, None).
    The caller must supply resolved target info in spec.config:
      - config["target_uuid"]: pre-minted componentUuid of the target canvas
      - config["target_name"]: canonical canvas name (e.g. "2. Second Canvas")
    These are injected by canvases.py's name→uuid map before calling render_component_nodes,
    or by the modifier's structure.py which resolves against the existing export's components.
    """
    target_uuid: str = spec.config.get("target_uuid", "")
    target_name: str = spec.config.get("target_name", spec.config.get("target", ""))

    # Build the node Name/label. Unlike talk_goto (which speaks), goto_mr is silent.
    # Use prompt as the label if provided, otherwise use node id.
    text = spec.prompt

    canvas = {
        "view": "react-shape-view",
        "component": {
            "props": {
                "text": "Exit Node",
                "list": list(component_nav) if component_nav else [],
                "type": 2,
            }
        },
        "size": {"width": 234, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -450, "y": 390},
        "zIndex": 2,
    }

    data: dict = {
        "appoint_node_id": "",
        "speakType": 1,
        "hitKnowledgeRate": [],
        "intention_judgment_time": 0.8,
        "type": 9,
        "repeat_script_type": 0,
        "hot_words_list": [],
        "specificComponentName": target_name,
        "hangupRate": "0.0%",
        "exclusive_key_words": [],
        "can_be_interrupted": 0,
        "id": node_uuid,
        "node_repetition": 0,
        "selected": False,
        "hitKnowledgeCountsRate": "0.0%",
        "multiple_appoint_id": target_uuid,
        "allow_jump_knowledges_switch": 1,
        "allow_jump_knowledges": [],
        "is_transfer": 0,
        "appoint_knowledge_id": "",
        "list": [text],
        "is_default": is_default,
        "textareaList": [""],
        "nodeLabelArr": [],
        "node_language": node_language,
        "agent_type": "SYSTEM",
        "sms_id": "",
        "can_interrupt_percent": 80,
        "name": text if text else "Talk Node",
        "notices_info": [],
        "notice_send_type": 0,
        "position": {"x": -450, "y": 390},
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": text if text else "Talk Node",
        "type": 9,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [],
            "intents": [],
            "variables": [],
            "serviceCall": [],
            "sentence_cut": [],
        },
    }

    return node_obj, None


def _build_goto_kb_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,  # unused; accepted for uniform dispatch
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, None]:
    """Build one goto_kb node (type 8) ``node_obj``.

    Terminal: no ports, no SentenceCutSpeech row.  Returns (node_obj, None).
    The caller must supply the resolved knowledgeId in spec.config:
      - config["target_kid"]: pre-resolved knowledgeId of the target KB (int or str)
    This is injected by canvases.py's kb_name_to_id map before calling render_component_nodes.

    Emits a topFloorDetails row (type 8) identical to the data dict.
    Ground truth from speech2572824560161596380.unpacked.json: appoint_knowledge_id is
    emitted as a STRING (e.g. "183805"), appoint_node_id/"specificComponentName"/
    "multiple_appoint_id" are all empty strings.
    """
    # appoint_knowledge_id is a STRING in real WIZ exports (confirmed: "183805" not 183805)
    target_kid: str = str(spec.config.get("target_kid", ""))

    canvas = {
        "view": "react-shape-view",
        "component": {
            "props": {
                "text": "Exit Node",
                "list": list(component_nav) if component_nav else [],
                "type": 2,
            }
        },
        "size": {"width": 234, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -450, "y": 390},
        "zIndex": 2,
    }

    data: dict = {
        "appoint_node_id": "",
        "speakType": 1,
        "hitKnowledgeRate": [],
        "intention_judgment_time": 2,
        "type": 8,
        "repeat_script_type": 0,
        "hot_words_list": [],
        "specificComponentName": "",
        "hangupRate": "0.0%",
        "exclusive_key_words": [],
        "openUserPauseDuration": False,
        "can_be_interrupted": 0,
        "id": node_uuid,
        "node_repetition": 0,
        "open_pause_duration": False,
        "selected": False,
        "hitKnowledgeCountsRate": "0.0%",
        "multiple_appoint_id": "",
        "openChasingDedayTim": False,
        "allow_jump_knowledges_switch": 0,
        "allow_jump_knowledges": list(kb_ids),
        "is_transfer": 0,
        "appoint_knowledge_id": target_kid,
        "is_default": is_default,
        "textareaList": [""],
        "nodeLabelArr": [],
        "node_language": node_language,
        "agent_type": "SYSTEM",
        "sms_id": "",
        "can_interrupt_percent": 80,
        "name": "Exit Node",
        "notices_info": [],
        "notice_send_type": 0,
        "position": {"x": -450, "y": 390},
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": "Exit Node",
        "type": 8,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [],
            "intents": [],
            "variables": [],
            "serviceCall": [],
            "sentence_cut": [],
        },
    }

    return node_obj, None


def _build_transfer_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,  # unused; accepted for uniform dispatch
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, dict]:
    """Build one Transfer-node (type 13) ``node_obj`` and ``scs_row``.

    Terminal: no ports.  Returns (node_obj, scs_row).
    Transfer nodes do NOT contribute a topFloorDetails row (confirmed by fixture 26).
    """
    text = spec.prompt
    xml = (
        '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">'
        f'<wiz:express-as style="default">{text}</wiz:express-as></speak>'
    )

    canvas = {
        "view": "react-shape-view",
        "component": {
            "props": {
                "text": "Exit Node",
                "list": list(component_nav) if component_nav else [],
                "type": 2,
            }
        },
        "size": {"width": 284, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -510, "y": 390},
        "zIndex": 2,
    }

    data: dict = {
        "agent_group": 1,
        "appoint_node_id": "",
        "speakType": 1,
        "hitKnowledgeRate": [],
        "intention_judgment_time": 2,
        "type": 13,
        "repeat_script_type": 0,
        "hot_words_list": [],
        "hangupRate": "0.0%",
        "exclusive_key_words": [],
        "dialog_list": [{"xml": xml, "html": f"<p>{text}</p>", "text": text}],
        "tag_list": [],
        "openUserPauseDuration": False,
        "can_be_interrupted": 0,
        "id": node_uuid,
        "node_repetition": 0,
        "open_pause_duration": False,
        "selected": False,
        "hitKnowledgeCountsRate": "0.0%",
        "multiple_appoint_id": "",
        "openChasingDedayTim": False,
        "allow_jump_knowledges_switch": 0,
        "allow_jump_knowledges": list(kb_ids),
        "is_transfer": 1,
        "appoint_knowledge_id": "",
        "list": [text],
        "is_default": is_default,
        "textareaList": [""],
        "nodeLabelArr": [],
        "node_language": node_language,
        "agent_type": "SYSTEM",
        "tts_language": node_language,
        "sms_id": "",
        "can_interrupt_percent": 0.8,
        "name": "Exit Node",
        "notices_info": [],
        "notice_send_type": 0,
        "position": {"x": -698.29, "y": 380.75},
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": "Exit Node",
        "type": 13,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [],
            "intents": [],
            "variables": [],
            "serviceCall": [],
            "sentence_cut": [],
        },
    }

    scs_row: dict = _build_scs_row(
        comp_uuid=comp_uuid,
        node_uuid=node_uuid,
        reccut_uuid=reccut_uuid,
        minter=minter,
        canvas_index=canvas_index,
        nid_str=spec.id,
        sort_index=sort_index,
        speech_id=speech_id,
        text=text,
    )

    return node_obj, scs_row


def _build_conditional_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, None]:
    """Build one Conditional-Judgment node (type 7). Router: one out-port per distinct
    branch name. No SentenceCutSpeech row, no topFloorDetails. Returns (node_obj, None).

    port_uuids maps branch-name -> port uuid (== all_client_intent id == routes key);
    render_component_nodes computes it from the distinct branch names in config.branches.
    """
    variable = spec.config.get("variable", "")
    branches = spec.config.get("branches", []) or []

    # distinct branch names, first-seen order (matches port_uuids ordering)
    port_names: list[str] = list(port_uuids.keys())

    items = [
        {"name": name, "id": port_uuids[name], "attrs": _fo(-37.67, 70), "group": "out"}
        for name in port_names
    ]
    canvas = {
        "view": "react-shape-view",
        "component": {"props": {
            "text": "Conditional Judgment Node",
            "list": list(component_nav) if component_nav else [],
            "type": 7,
        }},
        "size": {"width": 330, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -658.47, "y": 90.37},
        "ports": {
            "groups": {
                "in": {"position": {"name": "top"}, "attrs": _fo(-30, 140)},
                "out": {
                    "position": {"left": 200, "name": "bottom"},
                    "attrs": {"fo": {"magnet": "true", "height": 24}},
                },
            },
            "items": items,
        },
        "portMarkup": _PORT_MARKUP,
        "zIndex": 1,
    }

    # Resolve the variable's source: 0 = custom/user variable, 1 = system/collected variable.
    src: int = (var_source_by_name or {}).get(variable, 0)

    # rules: one entry per non-Default branch row; Default has no rule.
    rule_list: list[dict] = []
    node_vars: list[dict] = []
    for b in branches:
        if b.get("name") == "Default":
            continue
        cond: dict = {
            "variable_source": src,
            "left_value": variable,
            "operator": _WIZ_OPERATOR.get(b["op"], b["op"]),
        }
        if b["op"] not in ("IsNull", "NotNull"):
            if "value_var" in b:
                cond["right_value"] = b["value_var"]
                cond["type"] = "variable"
            else:
                cond["right_value"] = b["value"]
                cond["type"] = "const"
        rule_list.append({
            "name": b["name"],
            "branch_judgement_condition": [cond],
        })
        node_vars.append({"name": variable, "variableSource": src})

    all_client_intent = [
        {"name": name, "checked": True, "id": port_uuids[name]} for name in port_names
    ]

    data: dict = {
        "branchList": port_names,
        "client_intent": port_names,
        "node_variables": node_vars,
        "all_client_intent": all_client_intent,
        "hitKnowledgeRate": [],
        "type": 7,
        "is_default": is_default,
        "branch": rule_list,
        "node_language": node_language,
        "hot_words_list": [],
        "hangupRate": "0.0%",
        "name": "Conditional Judgment Node",
        "id": node_uuid,
        "position": {"x": -658.47, "y": 90.37},
        "selected": False,
        "hitKnowledgeCountsRate": "0.0%",
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": "Conditional Judgment Node",
        "type": 7,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [], "intents": [], "variables": [],
            "serviceCall": [], "sentence_cut": [],
        },
    }
    return node_obj, None


def _build_assign_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, None]:
    """Build one Variable-Assignment node (type 10). Silent pass-through with a single
    out-port named "Default". No SCS row, no topFloorDetails. Returns (node_obj, None)."""
    variable = spec.config.get("variable", "")
    value = spec.config.get("value", "")
    default_port = port_uuids["Default"]
    src: int = (var_source_by_name or {}).get(variable, 0)

    items = [{"name": "Default", "id": default_port, "attrs": _fo(-37.67, 70), "group": "out"}]
    canvas = {
        "view": "react-shape-view",
        "component": {"props": {
            "text": "Variable Assignment Node",
            "list": list(component_nav) if component_nav else [],
            "type": 10,
        }},
        "size": {"width": 244, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -293.05, "y": 112.54},
        "ports": {
            "groups": {
                "in": {"position": {"name": "top"}, "attrs": _fo(-30, 140)},
                "out": {
                    "position": {"left": 200, "name": "bottom"},
                    "attrs": {"fo": {"magnet": "true", "height": 24}},
                },
            },
            "items": items,
        },
        "portMarkup": _PORT_MARKUP,
        "zIndex": 1,
    }

    data: dict = {
        "sentence": [],
        "node_function": "",
        "node_variables": [{"name": variable, "variableSource": src}],
        "all_client_intent": [{"name": "Default", "checked": True, "id": default_port}],
        "allow_jump_knowledges": list(kb_ids),
        "hitKnowledgeRate": [],
        "value_assignment": [{
            "variable": {"name": variable, "speMark": f"~@##{variable}##@~"},
            "assign": {
                "func_output": {"type": "STRING"},
                "tag": "",
                "params": [{
                    "name": "value_to_assign", "label": "Assigned Value",
                    "type": "const", "value": value,
                }],
                "func_code": "OPT_VALUE_ASSIGNMENT",
                "func_name": "Set Value as",
            },
        }],
        "appoint_knowledge_id": "",
        "type": 10,
        "is_default": is_default,
        "textarea_list": [],
        "node_language": node_language,
        "hot_words_list": [],
        "tts_language": node_language,
        "hangupRate": "0.0%",
        "can_interrupt_percent": 0.8,
        "name": "Variable Assignment Node",
        "notices_info": [],
        "id": node_uuid,
        "position": {"x": -293.05, "y": 112.54},
        "selected": False,
        "hitKnowledgeCountsRate": "0.0%",
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": "Variable Assignment Node",
        "type": 10,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [], "intents": [], "variables": [],
            "serviceCall": [], "sentence_cut": [],
        },
    }
    return node_obj, None


def _build_exit_port_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,  # unused; accepted for uniform dispatch
    nested_exit_map: dict[str, dict[str, str]] | None = None,  # unused; uniform dispatch
) -> tuple[dict, None]:
    """Build one exit_port node (type 4) — a named exit point from a nested component.

    Terminal: no ports, no SentenceCutSpeech row.  Returns (node_obj, None).
    Distinct from goto_component: appoint_node_id and specificComponentName are EMPTY;
    the name (from config["name"]) labels the port that the parent component routes through.

    Emits a topFloorDetails row (add to the ("exit", "goto") condition in render_component_nodes).
    """
    name: str = spec.config.get("name", "Exit")

    canvas = {
        "view": "react-shape-view",
        "component": {
            "props": {
                "text": name,
                "list": list(component_nav) if component_nav else [],
                "type": 2,
            }
        },
        "size": {"width": 234, "height": 106},
        "shape": "react-shape",
        "id": node_uuid,
        "position": {"x": -450, "y": 390},
        "zIndex": 2,
    }

    data: dict = {
        "appoint_node_id": "",
        "speakType": 1,
        "hitKnowledgeRate": [],
        "intention_judgment_time": 2,
        "type": 4,
        "repeat_script_type": 0,
        "hot_words_list": [],
        "specificComponentName": "",
        "hangupRate": "0.0%",
        "exclusive_key_words": [],
        "openUserPauseDuration": False,
        "can_be_interrupted": 0,
        "id": node_uuid,
        "node_repetition": 0,
        "open_pause_duration": False,
        "selected": False,
        "hitKnowledgeCountsRate": "0.0%",
        "multiple_appoint_id": "",
        "openChasingDedayTim": False,
        "allow_jump_knowledges_switch": 0,
        "allow_jump_knowledges": list(kb_ids),
        "is_transfer": 0,
        "appoint_knowledge_id": "",
        "is_default": is_default,
        "textareaList": [""],
        "nodeLabelArr": [],
        "node_language": node_language,
        "agent_type": "SYSTEM",
        "sms_id": "",
        "can_interrupt_percent": 80,
        "name": name,
        "notices_info": [],
        "notice_send_type": 0,
        "position": {"x": -450, "y": 390},
    }

    node_obj: dict = {
        "canvas": canvas,
        "data": data,
        "name": name,
        "type": 4,
        "is_default": is_default,
        "data_extra": {
            "hot_words_list": [],
            "intents": [],
            "variables": [],
            "serviceCall": [],
            "sentence_cut": [],
        },
    }

    return node_obj, None


def _build_nested_node(
    spec: NodeSpec,
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    sort_index: int,
    port_uuids: dict[str, str],
    node_uuid: str,
    reccut_uuid: str,
    is_default: bool,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,
    nested_exit_map: dict[str, dict[str, str]] | None = None,
) -> tuple[dict, None]:
    """Type-11 nested-component delegator. Ports mirror the child's exit ports:
    port.uuid == child exit-node uuid (from nested_exit_map), port.id == minted.
    subComponentUuid is injected via spec.config['target_uuid'] by canvases.py.
    Returns (node_obj, None). No SCS, no topFloorDetails."""
    target_uuid = spec.config.get("target_uuid", "")
    target_name = spec.config.get("target", "")
    exits = (nested_exit_map or {}).get(target_name, {})  # {exit-name: child-exit-uuid}
    items = []
    for exit_name, child_exit_uuid in exits.items():
        items.append({
            "appointNodeId": "", "rate": "0.0%", "name": exit_name,
            "id": str(minter.uuid(f"nestport:{canvas_index}:{spec.id}:{exit_name}")),
            "uuid": child_exit_uuid,
            "attrs": _fo(-37.67, 73), "group": "out",
        })
    canvas = {
        "view": "react-shape-view",
        "component": {"props": {"text": spec.config.get("name", target_name),
                                "list": list(component_nav) if component_nav else [],
                                "type": 11}},
        "size": {"width": 293, "height": 106},
        "shape": "react-shape", "id": node_uuid, "position": {"x": -450, "y": 250},
        "ports": {"groups": {"in": {"position": {"name": "top"}, "attrs": _fo(-30, 140)},
                             "out": {"position": {"left": 200, "name": "bottom"},
                                     "attrs": {"fo": {"magnet": "true", "height": 24}}}},
                  "items": items},
        "portMarkup": _PORT_MARKUP, "zIndex": 1,
    }
    data = {
        "subComponentUuid": target_uuid, "name": target_name, "type": 11,
        "is_default": is_default, "isHangUp": False, "isJumpToKonwledge": False,
        "hitKnowledgeRate": [], "hangupRate": "0.0%", "hitKnowledgeCountsRate": "0.0%",
        "selected": False,
    }
    # FIX 1: envelope-level id = subComponentUuid (required by WIZ importer; absent → code:-1).
    node_obj = {"canvas": canvas, "data": data, "name": target_name, "type": 11,
                "is_default": is_default,
                "id": target_uuid,
                "data_extra": {"hot_words_list": [], "intents": [], "variables": [],
                               "serviceCall": [], "sentence_cut": []}}
    return node_obj, None


# ---------------------------------------------------------------------------
# Node-type dispatch registry
# ---------------------------------------------------------------------------

#: Maps node-type string → builder callable.
#: Each builder must accept the same keyword signature as ``_build_talk_node``
#: and return ``(node_obj, scs_row | None)``.
#: Goto returns scs_row=None (no SentenceCutSpeech row); exit/transfer return a real row.
NODE_BUILDERS: dict[str, Callable] = {
    "talk": _build_talk_node,
    "exit": _build_exit_node,
    "transfer": _build_transfer_node,
    "goto": _build_goto_node,
    "goto_mr": _build_goto_mr_node,
    "goto_kb": _build_goto_kb_node,
    "conditional": _build_conditional_node,
    "assign": _build_assign_node,
    "exit_port": _build_exit_port_node,
    "nested": _build_nested_node,
}


def _out_port_names(
    spec: NodeSpec,
    nested_exit_map: dict[str, dict[str, str]] | None = None,
) -> list[str]:
    """Distinct out-port names for a node, in canonical order, by type."""
    if spec.type == "talk":
        return list(_CHECKED)
    if spec.type == "assign":
        return ["Default"]
    if spec.type == "conditional":
        seen: list[str] = []
        for b in spec.config.get("branches", []) or []:
            name = b.get("name")
            if name and name not in seen:
                seen.append(name)
        return seen
    if spec.type == "nested":
        target = spec.config.get("target", "")
        exits = (nested_exit_map or {}).get(target, {})
        return list(exits.keys())
    return []  # terminal types (exit, transfer, goto, exit_port): no out-ports


# ---------------------------------------------------------------------------
# Main serializer
# ---------------------------------------------------------------------------

def render_component_nodes(
    nodes: list[NodeSpec],
    edges: list[EdgeSpec],
    *,
    canvas_index: int,
    comp_uuid: str,
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    minter: Any,
    component_nav: list[dict] | None = None,
    var_source_by_name: dict[str, int] | None = None,
    nested_exit_map: dict[str, dict[str, str]] | None = None,
) -> RenderedNodes:
    """Render a list of NodeSpec objects into WIZ.AI component sub-dicts.

    Parameters
    ----------
    nodes:
        Ordered list of nodes to render.
    edges:
        Outgoing edges between nodes. Drives entry-node detection and route wiring.
    canvas_index:
        The component's position index within BizSpeechComponent, used to scope
        minted UUIDs so two components on the same manifest never clash.
    comp_uuid:
        The BizSpeechComponent's ``componentUuid``.
    speech_id:
        The component's ``speechId`` (integer).
    branch_intent_ids:
        Mapping of branch name → intentId integer for the 5 system branches.
    kb_ids:
        List of knowledgeId strings for allow_jump_knowledges.
    node_language:
        Language code string (e.g. ``"3"`` for Bahasa Indonesia / default).
    minter:
        An ``IdMinter`` instance for deterministic UUID generation.
    component_nav:
        Optional list of component-nav dicts (all canvases in the bot) used to
        populate ``canvas.component.props.list`` on exit/transfer nodes.  When
        ``None`` (e.g. in unit tests), the list is left empty.
    var_source_by_name:
        Optional mapping of variable name → variableSource integer
        (0 = custom/user variable, 1 = system/collected variable).
        Built from the merged ``SpeechVariable`` list in ``apply_canvases`` after
        ``apply_variables`` has run.  When ``None`` (e.g. in unit tests or modifier
        calls), all variables default to source 0 (custom).
    nested_exit_map:
        Optional mapping of child-canvas-name → {exit-name: child-exit-node-uuid}.
        Used to wire a ``nested`` node's out-ports to the child component's exit_port
        node UUIDs so that routing keys in ``routes`` are the child-exit-node UUIDs
        (not freshly minted port UUIDs).  Injected by ``apply_canvases`` in Task 3
        after child canvases have been rendered.  When ``None``, nested nodes emit
        ports from an empty map (no port items; routes remains empty).
    """
    # Terminal node types: no out-ports, not in inbound_ports.
    _TERMINAL_TYPES = frozenset({"exit", "transfer", "goto", "goto_mr", "goto_kb", "exit_port"})

    details: dict = {}
    routes: dict = {}
    inbound_ports: list = []
    sentence_cut_speech: list = []
    top_floor_details: list = []

    # Synthesize conditional branch edges from config (Option A: targets live in the
    # node, not the canvas edges list). One edge per DISTINCT branch name -> its `to`.
    synth_edges: list[EdgeSpec] = list(edges)
    for spec in nodes:
        if spec.type == "conditional":
            seen: dict[str, str] = {}
            for b in spec.config.get("branches", []) or []:
                name, to = b.get("name"), b.get("to")
                if name and to and name not in seen:
                    seen[name] = to
            for name, to in seen.items():
                synth_edges.append(EdgeSpec(src=spec.id, branch=name, dst=to))

    # Compute entry nodes: nodes not targeted by any edge (using combined edge set).
    nodes_with_no_incoming: set[str] = {n.id for n in nodes}
    if synth_edges:
        nodes_with_no_incoming -= {e.dst for e in synth_edges}

    # Build node_id -> node_uuid and node_id -> port_uuid maps (filled during loop).
    _node_id_to_uuid: dict[str, str] = {}
    _node_id_to_port_uuids: dict[str, dict[str, str]] = {}
    # FIX 2: track node_id -> spec.type so edge wiring can set source.type=3 for nested nodes.
    _node_id_to_type: dict[str, str] = {n.id: n.type for n in nodes}

    for sort_index, spec in enumerate(nodes, start=1):
        nid_str = spec.id
        ci = canvas_index
        is_terminal = spec.type in _TERMINAL_TYPES

        node_uuid = str(minter.uuid(f"node:{ci}:{nid_str}"))
        reccut_uuid = str(minter.uuid(f"reccut:{ci}:{nid_str}"))
        is_default = nid_str in nodes_with_no_incoming

        # --- port UUIDs: type-dependent out-port names ---
        port_names = _out_port_names(spec, nested_exit_map)
        if spec.type == "nested":
            # Nested node routing keys are the CHILD exit-node UUIDs (not freshly minted).
            # This ensures routes[nested_uuid][child_exit_uuid] connects back to the child.
            target = spec.config.get("target", "")
            exits = (nested_exit_map or {}).get(target, {})
            port_uuids = dict(exits)  # {exit-name: child-exit-uuid}
        else:
            port_uuids: dict[str, str] = {
                name: str(minter.uuid(f"port:{ci}:{nid_str}:{name}")) for name in port_names
            }

        # Track mappings for edge wiring after the loop.
        _node_id_to_uuid[nid_str] = node_uuid
        # Terminal nodes have no out-ports — do NOT register in _node_id_to_port_uuids
        if not is_terminal:
            _node_id_to_port_uuids[nid_str] = port_uuids

        # --- dispatch to per-type builder ---
        builder = NODE_BUILDERS.get(spec.type)
        if builder is None:
            raise ValueError(f"unknown node type {spec.type!r}")

        node_obj, scs_row = builder(
            spec,
            canvas_index=canvas_index,
            comp_uuid=comp_uuid,
            speech_id=speech_id,
            branch_intent_ids=branch_intent_ids,
            kb_ids=kb_ids,
            node_language=node_language,
            minter=minter,
            sort_index=sort_index,
            port_uuids=port_uuids,
            node_uuid=node_uuid,
            reccut_uuid=reccut_uuid,
            is_default=is_default,
            component_nav=component_nav,
            var_source_by_name=var_source_by_name,
            nested_exit_map=nested_exit_map,
        )

        # --- accumulate ---
        details[node_uuid] = node_obj
        routes[node_uuid] = {}  # leaf/terminal nodes keep empty {}; outgoing edges fill in below

        if scs_row is not None:
            sentence_cut_speech.append(scs_row)

        # Only non-terminal entry nodes go into inbound_ports.
        if is_default and not is_terminal:
            inbound_ports.append({
                "name": _TYPE_NODE_NAME.get(spec.type, "Talk Node"),
                "type": _TYPE_INT.get(spec.type, 1),
                "uuid": node_uuid,
                "is_default": True,
            })

        # Exit (type 2), goto (type 4), goto_kb (type 8), and exit_port (type 4) contribute a
        # topFloorDetails row. Transfer (type 13) and nested (type 11) do NOT.
        if spec.type in ("exit", "goto", "goto_kb", "exit_port"):
            top_floor_details.append(node_obj["data"])

    # --- Wire edges into routes (user edges + synthesized conditional edges) ---
    for e in synth_edges:
        src_node_uuid = _node_id_to_uuid[e.src]
        dst_node_uuid = _node_id_to_uuid[e.dst]
        if e.branch not in _node_id_to_port_uuids.get(e.src, {}):
            raise ValueError(
                f"EdgeSpec branch {e.branch!r} not found in ports for node {e.src!r}"
            )
        src_port_uuid = _node_id_to_port_uuids[e.src][e.branch]
        edge_uuid = str(minter.uuid(f"edge:{canvas_index}:{e.src}:{e.branch}"))
        # FIX 2: nested (type-11) out-edges use source.type=3 (port-origin reference into child);
        # all other node types use source.type=1.
        src_type_int = 3 if _node_id_to_type.get(e.src) == "nested" else 1
        routes[src_node_uuid][src_port_uuid] = {
            "source": {"type": src_type_int, "uuid": src_port_uuid},
            "target": {"type": 1, "uuid": dst_node_uuid},
            "portDetail": {"id": edge_uuid, "zIndex": 3},
        }

    return RenderedNodes(
        details=details,
        routes=routes,
        inbound_ports=inbound_ports,
        sentence_cut_speech=sentence_cut_speech,
        top_floor_details=top_floor_details,
    )
