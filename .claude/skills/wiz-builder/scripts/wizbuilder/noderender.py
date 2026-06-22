"""wizbuilder.noderender — pure serializer for a single WIZ.AI canvas Talk Node.

Ported from the validated prototype scripts/proto_graph_emit.py::build_node.
Produces the exact node shape required by the WIZ.AI importer (reverse-engineered
and validated in Phase 1; see docs/node-serialization-spec.md).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Public dataclasses (consumed by Task 2+ callers — do NOT rename fields)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NodeSpec:
    id: str
    prompt: str


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
) -> RenderedNodes:
    """Render a list of NodeSpec objects into WIZ.AI component sub-dicts.

    For Task 1, edges=[] — every node is treated as an entry node (is_default=True,
    present in inbound_ports, routes entry is {}).

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
    """
    details: dict = {}
    routes: dict = {}
    inbound_ports: list = []
    sentence_cut_speech: list = []

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

        node_uuid = str(minter.uuid(f"node:{ci}:{nid_str}"))
        reccut_uuid = str(minter.uuid(f"reccut:{ci}:{nid_str}"))
        is_default = nid_str in nodes_with_no_incoming

        # --- port UUIDs for checked branches ---
        port_uuids: dict[str, str] = {
            b: str(minter.uuid(f"port:{ci}:{nid_str}:{b}")) for b in _CHECKED
        }

        # Track mappings for edge wiring after the loop.
        _node_id_to_uuid[nid_str] = node_uuid
        _node_id_to_port_uuids[nid_str] = port_uuids

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
        scs_row: dict = {
            "branch": "dev",
            "componentUuid": comp_uuid,
            "id": node_uuid,
            "isDelete": 0,
            "senRecName": "",
            "sentenceCutId": _wide_int(f"scid:{ci}:{nid_str}"),
            "sentenceText": text,
            "sentenceTextUrl": "",
            "showType": 0,
            "sortIndex": sort_index,
            "speechId": speech_id,
            "speechRecCutId": reccut_uuid,
            "type": "record",
        }

        # --- accumulate ---
        details[node_uuid] = node_obj
        routes[node_uuid] = {}  # leaf nodes keep empty {}; outgoing edges fill in below

        sentence_cut_speech.append(scs_row)

        if is_default:
            inbound_ports.append(
                {"name": "Talk Node", "type": 1, "uuid": node_uuid, "is_default": True}
            )

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
    )
