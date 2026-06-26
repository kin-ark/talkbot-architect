"""FlowEditor — pure in-memory wrapper for ONE BizSpeechComponent.

Decodes the four escaped-JSON fields (details, routes, inboundPorts, topFloorDetails)
and exposes read primitives.  Later tasks add edge/delete/content mutation on top.

Node→SCS link rule
------------------
Each SentenceCutSpeech row carries an ``"id"`` field that equals the node uuid in
``details`` (i.e. ``scs_row["id"] == node_uuid``).  ``scs_rows_for(uuid, all_scs)``
filters ``all_scs`` by ``componentUuid == comp["componentUuid"]`` and then by
``row["id"] == uuid``.  This rule is locked by ``test_scs_link_is_locked``.

Content/goto/cross-component primitives (Task 4)
-------------------------------------------------
``set_label``, ``set_prompt``, ``set_goto_target``, ``add_exit_node``,
``ensure_unclassified``, ``extract_node``, ``insert_node``.
"""

from __future__ import annotations

import copy as _copy
import json
import uuid as _uuid_mod
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

    # ------------------------------------------------------------------
    # Inbound rebuild
    # ------------------------------------------------------------------

    # Terminal int types: exit(2), transfer(13), goto/exit_port(4).
    # Entry nodes must not be terminal — mirrors the builder's
    # "is_default and not is_terminal" guard (noderender.py ~line 1235).
    _TERMINAL_TYPE_INTS: frozenset[int] = frozenset({2, 4, 13})

    def _rebuild_inbound(self) -> None:
        """Recompute self.inbound from the component's entry node(s).

        The builder emits ``inboundPorts`` as exactly the single node with
        ``data.is_default == True`` that is *not* a terminal type.  Mutations do
        not change the entry node, so we replicate the same rule here:

          • scan ``self.details`` for nodes where ``data.get("is_default")`` is
            truthy AND ``node["type"]`` not in {2, 4, 13};
          • emit one entry per such node (in practice exactly one);
          • field shape matches the builder exactly:
            ``{"name": <data.name>, "type": <int>, "uuid": <uuid>, "is_default": True}``.

        Do NOT key off route targets — that was wrong: a multi-node component
        with several route targets would emit one entry per target, which is
        inconsistent with every real deploy-verified build.
        """
        result: list[dict] = []
        for node_uuid, node_obj in self.details.items():
            data = node_obj.get("data") or {}
            if data.get("is_default") and node_obj.get("type", 0) not in self._TERMINAL_TYPE_INTS:
                result.append({
                    "name": data.get("name", ""),
                    "type": node_obj.get("type", 0),
                    "uuid": node_uuid,
                    "is_default": True,
                })
        self.inbound = result

    # ------------------------------------------------------------------
    # Edge mutation primitives
    # ------------------------------------------------------------------

    def set_edge_target(self, from_uuid: str, branch: str, to_uuid: str) -> None:
        """Set (or overwrite) the route for `branch` on `from_uuid` to point at `to_uuid`.

        Raises FlowEditError if `branch` is not a declared port on `from_uuid`.
        Calls _rebuild_inbound() after every change.
        """
        ports = self._ports(from_uuid)
        port_id = ports.get(branch)
        if port_id is None:
            raise FlowEditError(
                f"no port for branch {branch!r} on node {from_uuid!r}"
            )

        # Determine portDetail: reuse shape from an existing route, else mint one.
        # ALWAYS overwrite the id with a deterministic per-edge value so every
        # edge in the component has a unique portDetail.id (I1 fix).
        port_detail = self._sample_port_detail()
        det_uuid = str(
            _uuid_mod.uuid5(_uuid_mod.NAMESPACE_URL, f"{from_uuid}:{branch}")
        )
        if port_detail is None:
            port_detail = {"id": det_uuid, "zIndex": 3}
        else:
            port_detail["id"] = det_uuid

        # C2 fix: nested (type-11) out-edges need source.type=3 so the
        # deployed port→target link is intact.  All other node types use 1.
        # Mirrors noderender.py ~line 1260: src_type_int = 3 if nested else 1.
        src_type = 3 if self.details.get(from_uuid, {}).get("type") == 11 else 1

        edge = {
            "source": {"type": src_type, "uuid": port_id},
            "target": {"type": 1, "uuid": to_uuid},
            "portDetail": port_detail,
        }
        self.routes.setdefault(from_uuid, {})[port_id] = edge

        self._rebuild_inbound()

    def remove_edge(self, from_uuid: str, branch: str) -> None:
        """Remove the route for `branch` on `from_uuid`.

        The out-port itself is left intact in canvas.ports.items.
        Calls _rebuild_inbound() after the change.

        Raises FlowEditError if `branch` is not a declared port on `from_uuid`.
        """
        ports = self._ports(from_uuid)
        port_id = ports.get(branch)
        if port_id is None:
            raise FlowEditError(
                f"no port for branch {branch!r} on node {from_uuid!r}"
            )

        self.routes.get(from_uuid, {}).pop(port_id, None)

        self._rebuild_inbound()

    # ------------------------------------------------------------------
    # Node removal
    # ------------------------------------------------------------------

    def remove_node(
        self, uuid: str, all_scs: list[dict], all_sck: list[dict]
    ) -> dict:
        """Remove a node and cascade-clean all related tables.

        Steps:
        1. Unwire all inbound edges pointing at ``uuid`` (via remove_edge).
        2. Delete the node from details/routes/tfd/inbound.
        3. Remove SCS and SCK rows for this node from the shared lists (in-place).
        4. Rebuild inbound bookkeeping.
        5. Compute orphaned nodes: nodes in details (excluding entry node) that
           now have zero inbound edges.

        Returns:
            {
                "unwired_inbound": [(src_uuid, branch), ...],
                "orphaned": [uuid, ...],
                "removed_rows": <int>,   # total SCS + SCK rows deleted
            }

        The entry node is identified as the node whose ``inboundPorts`` entry has
        ``is_default: True`` (set by the builder for the component's start node).
        If no such node exists (e.g. an empty component), orphan detection is
        conservative: all zero-inbound nodes are reported.
        Does NOT cascade-delete orphans.
        """
        # I2 fix: unwire by iterating actual route port-ids, not branch-name
        # round-trip.  Two ports on the same source could both target `uuid`; a
        # branch-name round-trip via _ports() would resolve only one of them and
        # leave the other dangling.  Direct port-id deletion is unambiguous.
        unwired: list[tuple[str, str]] = []  # (src_uuid, branch_name) for report
        for src_uuid, port_map in list(self.routes.items()):
            if not isinstance(port_map, dict):
                continue
            # Build inverse port-id→branch map for reporting only.
            ports_inv = {v: k for k, v in self._ports(src_uuid).items()}
            for port_id in [
                pid for pid, edge in port_map.items()
                if (edge.get("target") or {}).get("uuid") == uuid
            ]:
                port_map.pop(port_id, None)
                branch_name = ports_inv.get(port_id, port_id)
                unwired.append((src_uuid, branch_name))

        # Identify entry node uuid (is_default=True in inboundPorts) BEFORE mutating inbound
        entry_uuid: str | None = next(
            (entry["uuid"] for entry in self.inbound if entry.get("is_default")),
            None,
        )

        # Step 2: delete node from core tables
        self.details.pop(uuid, None)
        self.routes.pop(uuid, None)
        self.tfd[:] = [row for row in self.tfd if row.get("id") != uuid]
        self.inbound[:] = [entry for entry in self.inbound if entry.get("uuid") != uuid]

        # Step 3: remove SCS rows from the shared list (in-place)
        comp_uuid = self.comp.get("componentUuid", "")
        removed_count = 0

        scs_to_remove = {
            id(row)
            for row in all_scs
            if row.get("componentUuid") == comp_uuid and row.get("id") == uuid
        }
        removed_count += len(scs_to_remove)
        all_scs[:] = [row for row in all_scs if id(row) not in scs_to_remove]

        # same id-link for SCK rows
        sck_to_remove = {
            id(row)
            for row in all_sck
            if row.get("componentUuid") == comp_uuid and row.get("id") == uuid
        }
        removed_count += len(sck_to_remove)
        all_sck[:] = [row for row in all_sck if id(row) not in sck_to_remove]

        # Step 4: rebuild inbound bookkeeping after direct table edits
        self._rebuild_inbound()

        # Step 5: compute orphaned nodes (zero inbound, not the entry node)
        orphaned: list[str] = [
            u
            for u in self.details
            if u != entry_uuid and not self.in_edges(u)
        ]

        return {
            "unwired_inbound": unwired,
            "orphaned": orphaned,
            "removed_rows": removed_count,
        }

    # ------------------------------------------------------------------
    # Content mutation primitives (Task 4)
    # ------------------------------------------------------------------

    def set_label(self, uuid: str, text: str) -> None:
        """Set the human-readable label of a node.

        Updates ``details[uuid]["data"]["name"]``.  Also updates the ``name`` field
        on any ``tfd`` row whose ``id`` matches the node uuid (exit/goto nodes
        carry their data dict as a tfd row — the two dicts are independent copies
        at this point, so both must be written).
        """
        node_obj = self.details.get(uuid)
        if node_obj is None:
            raise FlowEditError(f"no node with uuid {uuid!r}")
        node_obj.setdefault("data", {})["name"] = text
        for row in self.tfd:
            if row.get("id") == uuid and "name" in row:
                row["name"] = text

    def set_prompt(self, uuid: str, text: str, all_scs: list[dict]) -> None:
        """Update the spoken-text prompt of a talk or exit node.

        Writes to both places where the text lives:

        1. ``details[uuid]["data"]["dialog_list"]`` — rebuilds the single editorValue
           entry with the builder's canonical shape::

               {
                 "xml":  '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">'
                         '<wiz:express-as style="default">{text}</wiz:express-as></speak>',
                 "html": "<p>{text}</p>",
                 "text": "{text}",
               }

           The ``list`` convenience field (``data["list"]``) is also updated.

        2. Every ``SentenceCutSpeech`` row in ``all_scs`` that belongs to this node
           (``componentUuid == comp uuid`` AND ``id == uuid``) gets its
           ``sentenceText`` set to ``text``.

        Does NOT write tfd rows — tfd rows for exit nodes ARE the same data dict
        (by reference in the builder), but here they are separate copies.  The tfd
        row's text does not affect runtime playback; callers that need it in sync
        should call ``set_label`` afterwards if the label should also change.
        """
        node_obj = self.details.get(uuid)
        if node_obj is None:
            raise FlowEditError(f"no node with uuid {uuid!r}")
        xml = (
            '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">'
            f'<wiz:express-as style="default">{text}</wiz:express-as></speak>'
        )
        data = node_obj.setdefault("data", {})
        data["dialog_list"] = [{"xml": xml, "html": f"<p>{text}</p>", "text": text}]
        data["list"] = [text]
        # Update SCS rows
        comp_uuid = self.comp.get("componentUuid", "")
        for row in all_scs:
            if row.get("componentUuid") == comp_uuid and row.get("id") == uuid:
                row["sentenceText"] = text

    def set_goto_target(self, uuid: str, comp_uuid: str, comp_name: str) -> None:
        """Update the cross-component jump target on a goto node (type 4).

        Sets ``data["appoint_node_id"]`` and ``data["specificComponentName"]`` on the
        node object, and also updates the matching ``tfd`` row (``row["id"] == uuid``).

        Raises ``FlowEditError`` if the node does not exist.
        """
        node_obj = self.details.get(uuid)
        if node_obj is None:
            raise FlowEditError(f"no node with uuid {uuid!r}")
        data = node_obj.setdefault("data", {})
        data["appoint_node_id"] = comp_uuid
        data["specificComponentName"] = comp_name
        for row in self.tfd:
            if row.get("id") == uuid:
                row["appoint_node_id"] = comp_uuid
                row["specificComponentName"] = comp_name

    def add_exit_node(self, minter=None) -> tuple[str, dict]:
        """Mint and insert a new type-2 Exit node into this component.

        The uuid is deterministic::

            uuid5(NAMESPACE_URL, f"{componentUuid}:exit:{len(details)}")

        The node body is built via the ``_build_exit_node`` builder from
        ``wizbuilder.noderender`` (same path ``append_node`` uses) with an empty
        prompt, empty kb_ids, and default IDN language ``"3"``.

        Inserts into ``self.details``, sets ``self.routes[uuid] = {}`` (terminal),
        and appends the ``topFloorDetails`` row (``node_obj["data"]``).

        Parameters
        ----------
        minter:
            An ``IdMinter`` instance used to generate a stable ``sentenceCutId``
            on the returned SCS row.  When ``None`` the row's ``sentenceCutId``
            is derived from an empty manifest-hash seed (still a non-zero int, but
            not collision-safe across components).  Pass a real minter in production
            callers so the row is recording-complete on deploy.

        Returns
        -------
        tuple[str, dict]
            ``(uuid, scs_row)`` — the minted node uuid and the
            ``SentenceCutSpeech`` row (``sentenceText="(exit)"``).  The caller is
            responsible for appending ``scs_row`` to the export-level
            ``SentenceCutSpeech`` list; ``FlowEditor`` does not own that list.
        """
        import sys as _sys
        from pathlib import Path as _Path

        # Cross-skill import: wiz-builder is a sibling package.
        _builder_scripts = str(
            _Path(__file__).resolve().parents[4] / "wiz-builder" / "scripts"
        )
        if _builder_scripts not in _sys.path:
            _sys.path.insert(0, _builder_scripts)

        from wizbuilder.noderender import NodeSpec, _build_exit_node  # type: ignore[import]

        comp_uuid = self.comp.get("componentUuid", "")
        node_uuid = str(
            _uuid_mod.uuid5(
                _uuid_mod.NAMESPACE_URL,
                f"{comp_uuid}:exit:{len(self.details)}",
            )
        )
        spec = NodeSpec(id="exit", prompt="(exit)", type="exit")
        node_obj, scs_row = _build_exit_node(
            spec,
            canvas_index=0,
            comp_uuid=comp_uuid,
            speech_id=0,
            branch_intent_ids={
                "Positive": 0,
                "Negative": 0,
                "Reject": 0,
                "Unclassified": 0,
                "No answer": 0,
            },
            kb_ids=[],
            node_language="3",
            minter=minter,
            sort_index=1,
            port_uuids={},
            node_uuid=node_uuid,
            reccut_uuid="",
            is_default=False,
        )
        self.details[node_uuid] = node_obj
        self.routes[node_uuid] = {}
        self.tfd.append(node_obj["data"])
        return node_uuid, scs_row

    def ensure_unclassified(self, uuid: str) -> bool:
        """Ensure the node at ``uuid`` has an ``Unclassified`` out-port.

        If the port is already present, returns ``False`` (no-op).
        If absent, appends a new port item to ``canvas.ports.items``, copying
        the ``attrs`` and ``group`` from the first existing out-port item (or
        using defaults if the node has no ports yet), and minting a deterministic
        port uuid via::

            uuid5(NAMESPACE_URL, f"{uuid}:port:Unclassified")

        Returns ``True`` if the port was added.

        Raises ``FlowEditError`` if the node does not exist.
        """
        node_obj = self.details.get(uuid)
        if node_obj is None:
            raise FlowEditError(f"no node with uuid {uuid!r}")
        if "Unclassified" in self._ports(uuid):
            return False
        items = (
            (node_obj.get("canvas") or {})
            .get("ports", {})
            .get("items", [])
        )
        # Copy attrs/group from an existing out-port; fall back to safe defaults.
        _default_attrs = {
            "fo": {"x": -37.67, "width": 70, "y": -30, "magnet": "true", "height": 24}
        }
        if items:
            existing = items[0]
            attrs = _copy.deepcopy(existing.get("attrs", _default_attrs))
            group = existing.get("group", "out")
        else:
            attrs = _copy.deepcopy(_default_attrs)
            group = "out"
        new_port_id = str(
            _uuid_mod.uuid5(_uuid_mod.NAMESPACE_URL, f"{uuid}:port:Unclassified")
        )
        items.append({"name": "Unclassified", "id": new_port_id, "attrs": attrs, "group": group})
        # Ensure the items list is wired back into the node's canvas.
        node_obj.setdefault("canvas", {}).setdefault("ports", {})["items"] = items
        return True

    # ------------------------------------------------------------------
    # Cross-component move primitives (Task 4)
    # ------------------------------------------------------------------

    def extract_node(
        self, uuid: str, all_scs: list[dict], all_sck: list[dict]
    ) -> dict:
        """Extract a node and its associated rows from this editor as a portable payload.

        Like ``remove_node`` but the SCS/SCK rows that belong to the node are
        NOT deleted from ``all_scs``/``all_sck`` — they are deep-copied into the
        payload so the caller can insert them into another component.

        Steps:
        1. Collect deep-copies of the node's SCS and SCK rows.
        2. Unwire all inbound edges pointing at ``uuid`` (via ``remove_edge``).
        3. Remove the node from ``details``, ``routes``, ``tfd``, ``inbound`` (same as
           ``remove_node``), BUT do NOT touch ``all_scs`` / ``all_sck``.
        4. Rebuild inbound bookkeeping.

        Returns a payload dict::

            {
                "node_obj":     <deep-copied node object>,
                "routes_entry": <deep-copied routes sub-dict (or {})>,
                "tfd_row":      <deep-copied tfd row, or None>,
                "scs_rows":     [<deep-copied SCS rows>],
                "sck_rows":     [<deep-copied SCK rows>],
            }
        """
        if uuid not in self.details:
            raise FlowEditError(f"no node with uuid {uuid!r}")
        comp_uuid = self.comp.get("componentUuid", "")

        # Step 1: collect deep-copies of the rows BEFORE touching the tables.
        scs_rows = _copy.deepcopy([
            row for row in all_scs
            if row.get("componentUuid") == comp_uuid and row.get("id") == uuid
        ])
        sck_rows = _copy.deepcopy([
            row for row in all_sck
            if row.get("componentUuid") == comp_uuid and row.get("id") == uuid
        ])
        node_obj = _copy.deepcopy(self.details[uuid])
        routes_entry = _copy.deepcopy(self.routes.get(uuid, {}))
        tfd_row = _copy.deepcopy(
            next((r for r in self.tfd if r.get("id") == uuid), None)
        )

        # Step 2: unwire inbound edges by port-id (I2 fix — same as remove_node).
        for _src_uuid, port_map in list(self.routes.items()):
            if not isinstance(port_map, dict):
                continue
            for port_id in [
                pid for pid, edge in port_map.items()
                if (edge.get("target") or {}).get("uuid") == uuid
            ]:
                port_map.pop(port_id, None)

        # Step 3: remove from core tables (do NOT touch all_scs / all_sck).
        self.details.pop(uuid, None)
        self.routes.pop(uuid, None)
        self.tfd[:] = [row for row in self.tfd if row.get("id") != uuid]
        self.inbound[:] = [entry for entry in self.inbound if entry.get("uuid") != uuid]

        # Step 4: rebuild inbound.
        self._rebuild_inbound()

        return {
            "node_obj": node_obj,
            "routes_entry": routes_entry,
            "tfd_row": tfd_row,
            "scs_rows": scs_rows,
            "sck_rows": sck_rows,
        }

    def insert_node(
        self,
        payload: dict,
        dest_scs: list[dict],
        dest_sck: list[dict],
    ) -> None:
        """Insert a node payload (from ``extract_node``) into this editor.

        The node uuid is preserved exactly — no re-minting.

        The ``componentUuid`` on every carried SCS/SCK row is rewritten to this
        component's ``componentUuid`` before appending to ``dest_scs``/``dest_sck``.

        Parameters
        ----------
        payload:
            Dict produced by ``extract_node``:
            ``{node_obj, routes_entry, tfd_row, scs_rows, sck_rows}``.
        dest_scs:
            The destination component's ``SentenceCutSpeech`` list (mutated
            in-place).  Pass an empty list to ignore SCS rows.
        dest_sck:
            The destination component's ``SentenceCutKnowledge`` list (mutated
            in-place).  Pass an empty list to ignore SCK rows.
        """
        node_obj = payload["node_obj"]
        node_uuid: str = (node_obj.get("data") or {}).get("id") or ""
        if not node_uuid:
            # Fall back to scanning canvas id
            node_uuid = (node_obj.get("canvas") or {}).get("id", "")
        if not node_uuid:
            raise FlowEditError("payload node_obj has no resolvable uuid (data.id / canvas.id)")

        dest_comp_uuid = self.comp.get("componentUuid", "")

        self.details[node_uuid] = _copy.deepcopy(node_obj)
        self.routes[node_uuid] = _copy.deepcopy(payload.get("routes_entry") or {})
        tfd_row = payload.get("tfd_row")
        if tfd_row is not None:
            self.tfd.append(_copy.deepcopy(tfd_row))
        self._rebuild_inbound()

        for row in payload.get("scs_rows") or []:
            new_row = _copy.deepcopy(row)
            new_row["componentUuid"] = dest_comp_uuid
            dest_scs.append(new_row)
        for row in payload.get("sck_rows") or []:
            new_row = _copy.deepcopy(row)
            new_row["componentUuid"] = dest_comp_uuid
            dest_sck.append(new_row)

    # ------------------------------------------------------------------
    # Private helpers for edge mutation
    # ------------------------------------------------------------------

    def _sample_port_detail(self) -> dict | None:
        """Return a copy of the first portDetail found in any route of this component.

        Returns None if no routes exist yet.
        """
        for port_map in self.routes.values():
            if not isinstance(port_map, dict):
                continue
            for edge in port_map.values():
                pd = edge.get("portDetail")
                if pd and isinstance(pd, dict):
                    return _copy.deepcopy(pd)
        return None

