"""set-node-tags: assign disposition tags to a node in an existing export.

Resolves category+value by NAME against the export's existing SpeechTag
(real tenant ids); appends an absent category / value so node refs always
resolve (checker-clean). Recomputes kbTag. Replace semantics.
"""

from __future__ import annotations

from typing import Any

from wizbuilder.tags import _TAG_TS

from wizmodifier import codec
from wizmodifier.floweditor import FlowEditError, FlowEditor
from wizmodifier.io import InputBundle
from wizmodifier.ops._bsc import get_components, set_components


def _find_node_component(comps: list[dict], node_ref: dict) -> tuple[int, FlowEditor, str]:
    """Locate the single component whose details contain node_ref; return
    (index, FlowEditor, uuid). Ambiguous or missing -> ValueError."""
    hits: list[tuple[int, FlowEditor, str]] = []
    for i, comp in enumerate(comps):
        fe = FlowEditor(comp)
        try:
            uuid = fe.resolve(node_ref)
        except (FlowEditError, KeyError, ValueError):
            continue
        hits.append((i, fe, uuid))
    if not hits:
        raise ValueError(f"set-node-tags: node {node_ref!r} not found in any component")
    if len(hits) > 1:
        raise ValueError(f"set-node-tags: node ref {node_ref!r} is ambiguous "
                         f"(matches {len(hits)} components)")
    return hits[0]


def _default_ent_id(speech_tag: list[dict]) -> Any:
    for c in speech_tag:
        if c.get("entId") not in (None, ""):
            return c["entId"]
    return 0


def _resolve_category(speech_tag: list[dict], name: str, value_names: list[str],
                      minter) -> dict:
    """Find (or append) the category named `name` in speech_tag; ensure every
    value in value_names exists (append minted rows). Return the category dict."""
    cat = next((c for c in speech_tag if c.get("name") == name), None)
    if cat is None:
        cat = {
            "id": minter.int_id(f"tag:{name}"),
            "name": name, "isMutex": 0, "type": 0, "tagProperty": 0,
            "entId": _default_ent_id(speech_tag),
            "createTime": _TAG_TS, "modifyTime": _TAG_TS,
            "bizTagPropertyDTOS": [],
        }
        speech_tag.append(cat)
    have = {p.get("value") for p in cat["bizTagPropertyDTOS"]}
    for v in value_names:
        if v not in have:
            cat["bizTagPropertyDTOS"].append({
                "id": minter.int_id(f"tagval:{name}:{v}"),
                "tagId": cat["id"], "value": v,
            })
    return cat


def _denormalize(cat: dict, value_names: list[str]) -> dict:
    """Build a denormalized node tag_list entry from a SpeechTag category dict:
    header with STRING ids + only the SELECTED value rows (active:True)."""
    by_name = {p["value"]: p for p in cat["bizTagPropertyDTOS"]}
    return {
        "id": str(cat["id"]),
        "name": cat["name"],
        "isMutex": cat.get("isMutex", 0),
        "type": cat.get("type", 0),
        "tagProperty": cat.get("tagProperty", 0),
        "entId": str(cat.get("entId", "")),
        "createTime": cat.get("createTime", _TAG_TS),
        "modifyTime": cat.get("modifyTime", _TAG_TS),
        "bizTagPropertyDTOS": [
            {"id": str(by_name[v]["id"]), "tagId": str(cat["id"]),
             "value": v, "active": True}
            for v in value_names
        ],
    }


def _recompute_kbtag(comps: list[dict]) -> list[int]:
    """Sorted unique category ids referenced by any node's tag_list."""
    ids: set[int] = set()
    for comp in comps:
        details = codec.decode(comp.get("details") or "{}") or {}
        for node in details.values():
            for cat in (node.get("data") or {}).get("tag_list") or []:
                cid = cat.get("id")
                if cid is not None:
                    ids.add(int(cid))
    return sorted(ids)


def set_node_tags(bundle: InputBundle, params: dict, minter) -> None:
    node_ref = params.get("node")
    if not isinstance(node_ref, dict):
        raise ValueError("set-node-tags: 'node' ref (uuid or label) required")
    assignments = params.get("tags")
    if not isinstance(assignments, list):
        raise ValueError("set-node-tags: 'tags' must be a list of {category, values}")
    for a in assignments:
        if not isinstance(a, dict) or "category" not in a or not isinstance(a.get("values"), list):
            raise ValueError("set-node-tags: each tag needs 'category' and a 'values' list")
        if len(a.get("values", [])) == 0:
            raise ValueError(
                f"set-node-tags: tag assignment for category {a['category']!r} has no values"
            )

    comps = get_components(bundle)
    idx, fe, uuid = _find_node_component(comps, node_ref)

    speech_tag = codec.decode(bundle.data.get("SpeechTag", "[]")) or []
    tag_list = []
    for a in assignments:
        cat = _resolve_category(speech_tag, a["category"], a["values"], minter)
        tag_list.append(_denormalize(cat, a["values"]))

    fe.set_tags(uuid, tag_list)
    fe.flush()  # writes back into comps[idx] in place (same dict FlowEditor wraps)
    set_components(bundle, comps)
    bundle.data["SpeechTag"] = codec.encode(speech_tag)
    bundle.data["kbTag"] = _recompute_kbtag(get_components(bundle))
