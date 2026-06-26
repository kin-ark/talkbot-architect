"""FlowEditor — pure in-memory wrapper for ONE BizSpeechComponent.

Decodes the four escaped-JSON fields (details, routes, inboundPorts, topFloorDetails)
and exposes read primitives.  Later tasks add edge/delete/content mutation on top.

Node→SCS link rule
------------------
Each SentenceCutSpeech row carries an ``"id"`` field that equals the node uuid in
``details`` (i.e. ``scs_row["id"] == node_uuid``).  ``scs_rows_for(uuid, all_scs)``
filters ``all_scs`` by ``componentUuid == comp["componentUuid"]`` and then by
``row["id"] == uuid``.  This rule is locked by ``test_scs_link_is_locked``.
"""

from __future__ import annotations

import json
from typing import Any


class FlowEditError(ValueError):
    """Raised by FlowEditor when a resolve/lookup fails."""


def _decode(raw: Any, empty: Any) -> Any:
    """Decode an escaped-JSON field; treat None/empty-string/"null" as `empty`."""
    if raw is None or raw == "" or raw == "null":
        return empty
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return empty
    return raw


class FlowEditor:
    """Wraps a single BizSpeechComponent dict, decoding its flow payload.

    Fields decoded in __init__ and kept as live Python objects:
        self.details  – dict  {node_uuid: node_obj}
        self.routes   – dict  {node_uuid: {port_uuid: edge_obj}}
        self.inbound  – list  [{name, type, uuid, is_default}]
        self.tfd      – list  topFloorDetails rows
        self.comp     – the original component dict (mutated by flush())
    """

    def __init__(self, component: dict) -> None:
        self.comp = component

        raw_details = component.get("details")
        self.details: dict = _decode(raw_details, {})
        if not isinstance(self.details, dict):
            self.details = {}

        raw_routes = component.get("routes")
        self.routes: dict = _decode(raw_routes, {})
        if not isinstance(self.routes, dict):
            # routes may have been serialised as a list in old exports (add-bsc-keys default "[]")
            self.routes = {}

        raw_inbound = component.get("inboundPorts")
        self.inbound: list = _decode(raw_inbound, [])
        if not isinstance(self.inbound, list):
            self.inbound = []

        raw_tfd = component.get("topFloorDetails")
        self.tfd: list = _decode(raw_tfd, [])
        if not isinstance(self.tfd, list):
            self.tfd = []

    # ------------------------------------------------------------------
    # Flush — re-encode live dicts back into self.comp
    # ------------------------------------------------------------------

    def flush(self) -> None:
        """Re-encode all four live fields back into self.comp (compact JSON, no-ascii-escape)."""
        self.comp["details"] = json.dumps(self.details, ensure_ascii=False, separators=(",", ":"))
        self.comp["routes"] = json.dumps(self.routes, ensure_ascii=False, separators=(",", ":"))
        self.comp["inboundPorts"] = json.dumps(
            self.inbound, ensure_ascii=False, separators=(",", ":")
        )
        self.comp["topFloorDetails"] = json.dumps(
            self.tfd, ensure_ascii=False, separators=(",", ":")
        )

    # ------------------------------------------------------------------
    # resolve
    # ------------------------------------------------------------------

    def resolve(self, ref: dict) -> str:
        """Resolve a uuid-or-label reference to a node uuid.

        ``ref`` may carry:
            {"uuid": "<uuid>"}   – verified to exist in details; raises on miss.
            {"label": "<name>"}  – looked up by data.name; raises on 0 or >1 match.

        Raises FlowEditError on miss or ambiguous label.
        """
        if "uuid" in ref:
            u = ref["uuid"]
            if u not in self.details:
                raise FlowEditError(f"no node with uuid {u!r}")
            return u
        if "label" in ref:
            label = ref["label"]
            candidates = [
                u for u, n in self.details.items()
                if (n.get("data") or {}).get("name") == label
            ]
            if not candidates:
                raise FlowEditError(f"no node with label {label!r}")
            if len(candidates) > 1:
                raise FlowEditError(
                    f"ambiguous label {label!r}: not unique — candidates {candidates}"
                )
            return candidates[0]
        raise FlowEditError(f"ref must contain 'uuid' or 'label', got {ref!r}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ports(self, uuid: str) -> dict[str, str]:
        """Return {branch_name: port_uuid} from the node's canvas.ports.items."""
        node_obj = self.details.get(uuid, {})
        items = (
            (node_obj.get("canvas") or {})
            .get("ports", {})
            .get("items", []) or []
        )
        return {it["name"]: it["id"] for it in items}

    # ------------------------------------------------------------------
    # Graph read primitives
    # ------------------------------------------------------------------

    def node_type(self, uuid: str) -> int:
        """Return the WIZ int type of a node (1=talk, 2=exit, 4=goto/exit_port, ...)."""
        node_obj = self.details.get(uuid)
        if node_obj is None:
            raise FlowEditError(f"no node with uuid {uuid!r}")
        return node_obj.get("type", 0)

    def out_edges(self, uuid: str) -> list[tuple[str, str]]:
        """Return [(branch_name, target_uuid)] for all routed out-ports of the node.

        Ports that have no route entry (unconnected) are omitted — see unconnected_branches().
        """
        result: list[tuple[str, str]] = []
        node_routes = self.routes.get(uuid, {})
        for branch, port_id in self._ports(uuid).items():
            edge = node_routes.get(port_id)
            if edge:
                target_uuid = (edge.get("target") or {}).get("uuid")
                if target_uuid:
                    result.append((branch, target_uuid))
        return result

    def in_edges(self, uuid: str) -> list[tuple[str, str, str]]:
        """Return [(src_uuid, branch_name, uuid)] for all routes that target this node.

        Scans all routes in the component.
        """
        result: list[tuple[str, str, str]] = []
        for src_uuid, port_map in self.routes.items():
            if not isinstance(port_map, dict):
                continue
            src_ports_inv = {v: k for k, v in self._ports(src_uuid).items()}
            for port_id, edge in port_map.items():
                target_uuid = (edge.get("target") or {}).get("uuid")
                if target_uuid == uuid:
                    branch = src_ports_inv.get(port_id, port_id)
                    result.append((src_uuid, branch, uuid))
        return result

    def has_exit(self) -> bool:
        """Return True if any node in this component has type 2 (exit/hangup)."""
        return any(n.get("type") == 2 for n in self.details.values())

    def unconnected_branches(self) -> list[tuple[str, str]]:
        """Return [(node_uuid, branch_name)] for out-ports that have no route target.

        A branch is unconnected when:
        - its port_uuid is absent from routes[node_uuid], OR
        - the route entry has no non-empty target.uuid.
        """
        result: list[tuple[str, str]] = []
        for uuid in self.details:
            node_routes = self.routes.get(uuid, {})
            for branch, port_id in self._ports(uuid).items():
                edge = node_routes.get(port_id)
                if not edge:
                    result.append((uuid, branch))
                else:
                    target_uuid = (edge.get("target") or {}).get("uuid", "")
                    if not target_uuid:
                        result.append((uuid, branch))
        return result

    # ------------------------------------------------------------------
    # SCS link
    # ------------------------------------------------------------------

    def scs_rows_for(self, uuid: str, all_scs: list[dict]) -> list[dict]:
        """Return SentenceCutSpeech rows that belong to this node.

        Link rule: ``scs_row["id"] == node_uuid`` AND
                   ``scs_row["componentUuid"] == self.comp["componentUuid"]``.

        The ``"id"`` field on each SCS row is set to the node_uuid by the builder's
        ``_build_scs_row`` (noderender.py).  Filtering by componentUuid first avoids
        collisions when multiple components share a speechId.
        """
        comp_uuid = self.comp.get("componentUuid", "")
        return [
            row for row in all_scs
            if row.get("componentUuid") == comp_uuid and row.get("id") == uuid
        ]
