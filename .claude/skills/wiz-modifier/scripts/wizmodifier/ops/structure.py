"""Structure ops: add BSC keys, populate the details payload, add a component."""

from __future__ import annotations

from wizmodifier import codec
from wizmodifier.io import InputBundle
from wizmodifier.ops._bsc import get_components, require_component, set_components

# The 6 keys wiz-builder adds to every BSC entry (canvases.py:119-124).
DEFAULT_BSC_KEYS = {
    "inboundPorts": "[]",
    "outboundPorts": "[]",
    "routes": "[]",
    "nluConf": "{}",
    "sourceUuid": "",
    "topFloorDetails": "{}",
}


def add_bsc_keys(bundle: InputBundle, params: dict, minter) -> None:
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    keys = params.get("keys") or DEFAULT_BSC_KEYS
    comp.update(keys)
    set_components(bundle, comps)


def _build_details_payload(nodes: list[dict], minter, comp_index: int) -> dict:
    """Build the WIZ details envelope from a builder-style node list.

    Mirrors wiz-builder canvases.py:73-99. Each node dict has id, label,
    and parent (id of parent node, or None for the root).
    """
    envelope_uuid = str(minter.uuid(f"modifier-envelope:{comp_index}"))
    node_uuids = {
        n["id"]: str(minter.uuid(f"modifier-node:{comp_index}:{n['id']}"))
        for n in nodes
    }
    node_dicts = []
    for ni, n in enumerate(nodes):
        uid = node_uuids[n["id"]]
        parent = n.get("parent")
        node_dicts.append({
            "uuid": uid,
            "value": uid,
            "parentId": node_uuids[parent] if parent is not None else "",
            "label": n["label"],
            "sortIndex": ni,
            "sortIndexABS": ni,
            "editStatus": 1,
            "useStatus": 1,
            "children": [],
        })
    return {
        envelope_uuid: {
            "canvas": {"component": {"props": {"list": node_dicts}}}
        }
    }


def populate_details(bundle: InputBundle, params: dict, minter) -> None:
    comps = get_components(bundle)
    index = params["component"]
    comp = require_component(comps, index)
    payload = _build_details_payload(params["nodes"], minter, index)
    comp["details"] = codec.encode(payload)
    set_components(bundle, comps)
