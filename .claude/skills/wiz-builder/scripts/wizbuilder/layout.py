"""Assign WIZ-canvas node positions (data.top/data.left) via a layered BFS.

WIZ places canvas nodes using node['data']['top'] (y) and ['left'] (x). The
renderer leaves them unset, so every built node lands at the origin (a stack).
This lays each component out top-down: rank = BFS depth from the entry node,
column = order within a rank. Pure + deterministic; positions are advisory.
"""
from __future__ import annotations

from collections import deque


def _targets(routes: dict, uuid: str, present: set[str]) -> list[str]:
    """Intra-component destinations of `uuid`, in stable order, deduped."""
    out: list[str] = []
    seen: set[str] = set()
    ports = routes.get(uuid) or {}
    for _port, edge in sorted(ports.items()):
        if not isinstance(edge, dict):
            continue
        dst = (edge.get("target") or {}).get("uuid")
        if dst in present and dst not in seen:
            seen.add(dst)
            out.append(dst)
    return out


def _entry(details: dict) -> str | None:
    for uuid, node in details.items():
        if (node.get("data") or {}).get("is_default"):
            return uuid
    return None


def assign_positions(
    details: dict,
    routes: dict,
    *,
    row_gap: int = 150,
    col_gap: int = 260,
    origin_top: int = 80,
    origin_left: int = 120,
) -> None:
    """Write integer data.top/data.left into every node of `details` (in place)."""
    if not details:
        return
    present = set(details.keys())

    # entry: is_default → else a node with no intra-component inbound → else first key
    entry = _entry(details)
    if entry is None:
        has_inbound: set[str] = set()
        for u in details:
            has_inbound.update(_targets(routes, u, present))
        entry = next((u for u in details if u not in has_inbound), next(iter(details)))

    rank: dict[str, int] = {}
    order: list[str] = []          # discovery order (stable within a rank via BFS)
    q: deque[str] = deque([entry])
    rank[entry] = 0
    order.append(entry)
    while q:
        u = q.popleft()
        for dst in _targets(routes, u, present):
            if dst not in rank:
                rank[dst] = rank[u] + 1
                order.append(dst)
                q.append(dst)

    # orphans / unreached: stack after the deepest reached rank, one per row
    next_rank = (max(rank.values()) + 1) if rank else 0
    for u in details:
        if u not in rank:
            rank[u] = next_rank
            order.append(u)
            next_rank += 1

    # column index within each rank, following discovery order
    col_of: dict[str, int] = {}
    per_rank: dict[int, int] = {}
    for u in order:
        r = rank[u]
        col_of[u] = per_rank.get(r, 0)
        per_rank[r] = col_of[u] + 1

    for u in details:
        node = details[u]
        x = origin_left + col_of[u] * col_gap
        y = origin_top + rank[u] * row_gap
        data = node.setdefault("data", {})
        # data.top/left are secondary (absent on several node types); the field
        # WIZ actually renders from is the jointjs cell position, mirrored in
        # data.position AND canvas.position. Set all so the flow lays out.
        data["top"] = y
        data["left"] = x
        data["position"] = {"x": x, "y": y}
        canvas = node.setdefault("canvas", {})
        canvas["position"] = {"x": x, "y": y}
