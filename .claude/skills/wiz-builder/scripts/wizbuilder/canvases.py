"""apply_canvases: replace the empty template canvas with manifest-defined canvases.

WIZ.AI's BizSpeechComponent.details is a JSON-encoded string with the shape:

    {
      "<envelope_uuid>": {
        "canvas": {
          "component": {
            "props": {
              "list": [
                {"uuid": "...", "parentId": "", "label": "Greeting", "sortIndex": 0, ...},
                ...
              ]
            }
          }
        }
      }
    }

The envelope UUID is a top-level key; production exports may carry multiple
envelopes per component, but this MVP emits exactly one per canvas. Nodes
live at canvas.component.props.list.
"""

from __future__ import annotations

import json
from typing import Any

from wizbuilder.ids import IdMinter
from wizbuilder.manifest import Canvas, Manifest

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

    new_components = [
        _build_component(canvas, ci, manifest, minter, base, speech_id)
        for ci, canvas in enumerate(manifest.canvases)
    ]
    template["BizSpeechComponent"] = json.dumps(new_components, ensure_ascii=False, separators=(",", ":"))
    return template


def _build_component(
    canvas: Canvas,
    canvas_index: int,
    manifest: Manifest,
    minter: IdMinter,
    base: dict[str, Any],
    speech_id: int,
) -> dict[str, Any]:
    canvas_uuid = str(minter.uuid(f"component:{canvas_index}"))
    envelope_uuid = str(minter.uuid(f"envelope:{canvas_index}"))

    node_uuids: dict[str, str] = {}
    for node in canvas.nodes:
        seed = f"node:{canvas_index}:{node.id}"
        node_uuids[node.id] = str(minter.uuid(seed))

    node_dicts = []
    for ni, node in enumerate(canvas.nodes):
        uid = node_uuids[node.id]
        parent_uid = node_uuids[node.parent] if node.parent is not None else ""
        node_dicts.append({
            "uuid": uid,
            "value": uid,  # WIZ format duplicates uuid as value on every FlowNode
            "parentId": parent_uid,
            "label": node.label,
            "sortIndex": ni,
            "sortIndexABS": ni,
            "editStatus": 1,
            "useStatus": 1,
            "children": [],
        })

    details_payload = {
        envelope_uuid: {
            "canvas": {
                "component": {
                    "props": {
                        "list": node_dicts,
                    }
                }
            }
        }
    }

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
        "inboundPorts": "[]",
        "outboundPorts": "[]",
        "routes": "[]",
        "nluConf": "{}",
        "sourceUuid": "",
        "topFloorDetails": "{}",
        "details": json.dumps(details_payload, ensure_ascii=False, separators=(",", ":")),
    }

    if canvas_index > 0:
        for key in _SECONDARY_STRIP_KEYS:
            entry.pop(key, None)

    return entry
