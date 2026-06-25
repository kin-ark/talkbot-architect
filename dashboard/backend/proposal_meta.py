"""Pure helpers: structural change-set + plain-language summary for a proposal.

Inputs are agents.summarize() flow-model dicts (no I/O here)."""
from __future__ import annotations

import json


def _nodes_by_uuid(summary: dict) -> dict:
    out: dict = {}
    for comp in summary.get("components", []):
        for uuid, node in (comp.get("nodes") or {}).items():
            out[uuid] = node
    return out


def change_set(before: dict, after: dict) -> dict:
    bc = {c["uuid"] for c in before.get("components", [])}
    ac = {c["uuid"] for c in after.get("components", [])}
    bn = _nodes_by_uuid(before)
    an = _nodes_by_uuid(after)
    changed = [u for u in (bn.keys() & an.keys())
               if json.dumps(bn[u], sort_keys=True) != json.dumps(an[u], sort_keys=True)]
    return {
        "added_components": sorted(ac - bc),
        "removed_components": sorted(bc - ac),
        "added_nodes": sorted(an.keys() - bn.keys()),
        "removed_nodes": sorted(bn.keys() - an.keys()),
        "changed_nodes": sorted(changed),
    }


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def change_summary(cs: dict, checker_delta: dict | None) -> str:
    parts: list[str] = []
    if cs["added_components"]:
        parts.append(f"Adds {_plural(len(cs['added_components']), 'component')}")
    if cs["removed_components"]:
        parts.append(f"Removes {_plural(len(cs['removed_components']), 'component')}")
    if cs["added_nodes"]:
        parts.append(_plural(len(cs["added_nodes"]), "node") + " added")
    if cs["changed_nodes"]:
        parts.append(_plural(len(cs["changed_nodes"]), "node") + " changed")
    if cs["removed_nodes"]:
        parts.append(_plural(len(cs["removed_nodes"]), "node") + " removed")
    if not parts:
        parts.append("No structural changes")
    if checker_delta is not None:
        new = checker_delta["errors_after"] - checker_delta["errors_before"]
        if new > 0:
            parts.append(f"⚠ +{new} {'error' if new == 1 else 'errors'}")
        elif new < 0:
            parts.append(f"✓ {new} errors")
        else:
            parts.append("✓ 0 new errors")
    return " · ".join(parts)
