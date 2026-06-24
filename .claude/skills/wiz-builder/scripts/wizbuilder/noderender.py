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
        "portMarkup": [
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
                        "style": {
                            "background": "transparent",
                            "width": "100%",
                            "height": "100%",
                        },
                        "selector": "foBody",
                        "tagName": "body",
                        "attrs": {"xmlns": "http://www.w3.org/1999/xhtml"},
                    }
                ],
                "selector": "fo",
                "tagName": "foreignObject",
            }
        ],
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
}


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
    """
    # Terminal node types: no out-ports, not in inbound_ports.
    _TERMINAL_TYPES = frozenset({"exit", "transfer", "goto"})

    details: dict = {}
    routes: dict = {}
    inbound_ports: list = []
    sentence_cut_speech: list = []
    top_floor_details: list = []

    # Compute entry nodes: nodes not targeted by any edge.
    nodes_with_no_incoming: set[str] = {n.id for n in nodes}
    if edges:
        dst_ids = {e.dst for e in edges}
        nodes_with_no_incoming -= dst_ids

    # Build node_id -> node_uuid and node_id -> port_uuid maps (filled during loop).
    _node_id_to_uuid: dict[str, str] = {}
    _node_id_to_port_uuids: dict[str, dict[str, str]] = {}

    for sort_index, spec in enumerate(nodes, start=1):
        nid_str = spec.id
        ci = canvas_index
        is_terminal = spec.type in _TERMINAL_TYPES

        node_uuid = str(minter.uuid(f"node:{ci}:{nid_str}"))
        reccut_uuid = str(minter.uuid(f"reccut:{ci}:{nid_str}"))
        is_default = nid_str in nodes_with_no_incoming

        # --- port UUIDs for checked branches (Talk only; terminal nodes ignore these) ---
        port_uuids: dict[str, str] = {
            b: str(minter.uuid(f"port:{ci}:{nid_str}:{b}")) for b in _CHECKED
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
        )

        # --- accumulate ---
        details[node_uuid] = node_obj
        routes[node_uuid] = {}  # leaf/terminal nodes keep empty {}; outgoing edges fill in below

        if scs_row is not None:
            sentence_cut_speech.append(scs_row)

        # Only non-terminal entry nodes go into inbound_ports.
        if is_default and not is_terminal:
            inbound_ports.append(
                {"name": "Talk Node", "type": 1, "uuid": node_uuid, "is_default": True}
            )

        # Exit (type 2) and goto (type 4) contribute a topFloorDetails row = their data dict.
        # Transfer (type 13) does NOT (confirmed by fixture 26).
        if spec.type in ("exit", "goto"):
            top_floor_details.append(node_obj["data"])

    # --- Wire edges into routes ---
    for e in edges:
        src_node_uuid = _node_id_to_uuid[e.src]
        dst_node_uuid = _node_id_to_uuid[e.dst]
        if e.branch not in _node_id_to_port_uuids.get(e.src, {}):
            raise ValueError(
                f"EdgeSpec branch {e.branch!r} not found in ports for node {e.src!r}"
            )
        src_port_uuid = _node_id_to_port_uuids[e.src][e.branch]
        edge_uuid = str(minter.uuid(f"edge:{canvas_index}:{e.src}:{e.branch}"))
        routes[src_node_uuid][src_port_uuid] = {
            "source": {"type": 1, "uuid": src_port_uuid},
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
