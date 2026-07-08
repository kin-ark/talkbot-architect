"""apply_canvases: replace the empty template canvas with manifest-defined canvases.

Uses render_component_nodes (noderender.py) to produce the real WIZ.AI node shape
validated against the importer in Phase 1. Each canvas becomes one BizSpeechComponent
entry with fully-wired details, routes, inboundPorts, and SentenceCutSpeech rows.
"""

from __future__ import annotations

import json
from typing import Any

from wizbuilder.ids import IdMinter
from wizbuilder.layout import assign_positions
from wizbuilder.manifest import Canvas, Manifest
from wizbuilder.noderender import EdgeSpec, NodeSpec, render_component_nodes

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

# Map manifest language codes to WIZ.AI node_language strings.
# "3" is confirmed for IDN from reference exports.  All sampled exports (including
# an ENG-intent bot) also carry languageItem="3" in BizSpeechScene, so "3" is a
# safe placeholder for the remaining documented languages until per-language reference
# exports are decoded.
_LANGUAGE_MAP = {
    "IDN": "3",
    "ENG": "3",
    # TODO(lang-codes): verify ZHO/THA (and ENG) numeric codes from non-IDN reference exports
    # — "3" is an empirical placeholder and may mislabel NLU/TTS routing for these languages.
    "ZHO": "3",
    "THA": "3",
}


def apply_canvases(
    template: dict[str, Any],
    manifest: Manifest,
    minter: IdMinter,
    *,
    kb_id_by_name: dict[str, int] | None = None,
    tag_vocabulary=None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Replace the template's BizSpeechComponent list with manifest canvases.

    Returns (template, canvas_uuid_by_name) so callers can pass the UUID map to
    apply_knowledge_bases for multi-round linkage (Task 3).

    Parameters
    ----------
    kb_id_by_name:
        Optional pre-minted {kb.name: knowledgeId} map from compile.py.  When
        provided, the ids are appended to kb_ids so talk nodes include them in
        allow_jump_knowledges.  When None (legacy callers, unit tests), no
        manifest-KB ids are added.
    """
    raw = template.get("BizSpeechComponent")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            "apply_canvases requires template['BizSpeechComponent'] to be a non-empty JSON string"
        )
    template_bsc = json.loads(raw)
    base = template_bsc[0] if template_bsc else {}
    speech_id = base.get("speechId", 0)

    # Resolve branch_intent_ids from template SpeechIntent
    _system_branch_names = {"Positive", "Negative", "Reject", "Unclassified", "No answer"}
    speech_intents_raw = template.get("SpeechIntent", "[]")
    speech_intents = (
        json.loads(speech_intents_raw)
        if isinstance(speech_intents_raw, str)
        else speech_intents_raw
    )
    branch_intent_ids: dict[str, int] = {
        i["intentName"]: i["intentId"]
        for i in speech_intents
        if i.get("intentName") in _system_branch_names
    }

    # Resolve kb_ids from template BizKnowledgeInfo (baseline entries)
    biz_kb_raw = template.get("BizKnowledgeInfo", "[]")
    biz_kb = json.loads(biz_kb_raw) if isinstance(biz_kb_raw, str) else biz_kb_raw
    kb_ids: list[str] = [str(k["knowledgeId"]) for k in biz_kb]

    # Extend kb_ids with manifest-KB ids pre-minted by compile.py so that
    # talk nodes advertise them in allow_jump_knowledges before the KB entries
    # are actually appended by apply_knowledge_bases (which runs after apply_canvases).
    if kb_id_by_name:
        for kid in kb_id_by_name.values():
            kid_str = str(kid)
            if kid_str not in kb_ids:
                kb_ids.append(kid_str)

    # Build kb_name_to_id for goto_kb target resolution.
    # Merges baseline BizKnowledgeInfo (kdTitle→knowledgeId) with manifest-KB ids
    # (kb_id_by_name: name→id pre-minted by compile.py).  goto_kb nodes in any
    # canvas can resolve their config.target (a KB name) to the knowledgeId int.
    kb_name_to_id: dict[str, int] = {k["kdTitle"]: k["knowledgeId"] for k in biz_kb}
    if kb_id_by_name:
        kb_name_to_id.update(kb_id_by_name)

    # Resolve node_language from manifest.language
    node_language = _LANGUAGE_MAP.get(manifest.language)
    if node_language is None:
        raise ValueError(
            f"Unsupported manifest language {manifest.language!r}. "
            f"Only {sorted(_LANGUAGE_MAP)} are supported in this MVP."
        )

    # Pre-mint all component UUIDs so the component-nav list can be built before
    # any canvas is rendered (exit/transfer nodes need the full list).
    canvas_uuids: list[str] = [
        str(minter.uuid(f"component:{ci}")) for ci, _ in enumerate(manifest.canvases)
    ]

    # component_nav: one entry per canvas, in order.  Used by exit/transfer node
    # canvas.component.props.list.  The first canvas gets useStatus=2 (active/primary);
    # subsequent canvases get useStatus=1.
    component_nav: list[dict] = [
        {
            "sortIndexABS": ci + 1,
            "sortIndex": ci + 1,
            "editStatus": 1,
            "hangUpRate": "0.0%",
            "label": canvas.name,
            "title": canvas.name,
            "uuid": canvas_uuids[ci],
            "hitRate": "0.0%",
            "parentId": "",
            "componentUuid": canvas_uuids[ci],
            "useStatus": 2 if ci == 0 else 1,
            "children": [],
            "value": canvas_uuids[ci],
        }
        for ci, canvas in enumerate(manifest.canvases)
    ]

    # Build a name→componentUuid map for cross-canvas goto resolution.
    # canvases.py pre-mints all UUIDs so goto nodes in any canvas can resolve targets
    # that haven't been rendered yet.
    canvas_uuid_by_name: dict[str, str] = {
        canvas.name: canvas_uuids[ci] for ci, canvas in enumerate(manifest.canvases)
    }

    # Build var_source_by_name from the merged SpeechVariable (apply_variables has already run).
    # variableSource: 0 = custom/user variable, 1 = system/collected variable.
    speech_vars_raw = template.get("SpeechVariable", "[]")
    speech_vars = (
        json.loads(speech_vars_raw) if isinstance(speech_vars_raw, str) else speech_vars_raw
    )
    var_source_by_name: dict[str, int] = {
        v["name"]: v.get("variableSource", 0) for v in speech_vars
    }

    # Identify child canvases: any canvas named as a `nested` node's config.target.
    # parent_of_child maps child-canvas-name → parent-canvas-name.
    parent_of_child: dict[str, str] = {}
    for canvas in manifest.canvases:
        for node in canvas.nodes:
            if node.type == "nested":
                target = node.config.get("target", "")
                if target:
                    parent_of_child[target] = canvas.name

    child_names: set[str] = set(parent_of_child.keys())
    # Scope: one level of nesting — child canvases are not themselves parents (no nested-in-nested).

    # Multi-round target canvases: a KB's `multi_round` names the canvas it delegates into.
    # That component must carry category=2 so WIZ files it under the "Multi-Round Dialogue"
    # tab (category=1 = normal Main Talk-Flow). Decoded from the real export: every
    # KB-multipleAppointId target component has category=2.
    mr_target_names: set[str] = {
        kb.multi_round for kb in manifest.knowledge_bases if kb.multi_round
    }

    # Render order: children BEFORE parents (two-pass).
    # Pass 1: render child canvases; collect exit_port node UUIDs into nested_exit_map.
    # Pass 2: render parent (and non-nested) canvases with the populated nested_exit_map.
    #
    # nested_exit_map: {child-canvas-name: {exit-port-name: child-exit-node-uuid}}
    # The exit-port name is stored in node_obj["data"]["name"] (== config["name"]).
    nested_exit_map: dict[str, dict[str, str]] = {}

    # Maintain insertion order for the final component list (children first, then parents,
    # in their original manifest position within each group).
    child_canvases = [(ci, c) for ci, c in enumerate(manifest.canvases) if c.name in child_names]
    parent_canvases = [
        (ci, c) for ci, c in enumerate(manifest.canvases) if c.name not in child_names
    ]

    # We need a stable final ordering for new_components that matches the manifest order.
    # Build a ci→comp map, then emit in manifest order.
    comp_by_ci: dict[int, dict] = {}
    scs_by_ci: dict[int, list] = {}

    # Pass 1: render children
    for ci, canvas in child_canvases:
        comp, scs_rows = _build_component(
            canvas=canvas,
            canvas_index=ci,
            canvas_uuid=canvas_uuids[ci],
            manifest=manifest,
            minter=minter,
            base=base,
            speech_id=speech_id,
            branch_intent_ids=branch_intent_ids,
            kb_ids=kb_ids,
            node_language=node_language,
            component_nav=component_nav,
            canvas_uuid_by_name=canvas_uuid_by_name,
            var_source_by_name=var_source_by_name,
            nested_exit_map=nested_exit_map,
            parent_uuid=canvas_uuid_by_name.get(parent_of_child.get(canvas.name, ""), "0"),
            mr_target_names=mr_target_names,
            kb_name_to_id=kb_name_to_id,
            tag_vocabulary=tag_vocabulary,
        )
        comp_by_ci[ci] = comp
        scs_by_ci[ci] = scs_rows

        # After rendering the child, extract exit_port node UUIDs from its details.
        # details is a JSON string: {node_uuid: node_obj}; exit_port nodes have type==4
        # and their port name is node_obj["data"]["name"].
        details_dict: dict = json.loads(comp["details"])
        exit_map: dict[str, str] = {}
        for node_uuid, node_obj in details_dict.items():
            if node_obj.get("type") == 4 and node_obj["data"].get("specificComponentName") == "":
                # exit_port nodes have empty specificComponentName (unlike goto nodes).
                exit_map[node_obj["data"]["name"]] = node_uuid
        nested_exit_map[canvas.name] = exit_map

    # Pass 2: render parents (and any non-child canvases)
    for ci, canvas in parent_canvases:
        comp, scs_rows = _build_component(
            canvas=canvas,
            canvas_index=ci,
            canvas_uuid=canvas_uuids[ci],
            manifest=manifest,
            minter=minter,
            base=base,
            speech_id=speech_id,
            branch_intent_ids=branch_intent_ids,
            kb_ids=kb_ids,
            node_language=node_language,
            component_nav=component_nav,
            canvas_uuid_by_name=canvas_uuid_by_name,
            var_source_by_name=var_source_by_name,
            nested_exit_map=nested_exit_map,
            parent_uuid="0",
            mr_target_names=mr_target_names,
            kb_name_to_id=kb_name_to_id,
            tag_vocabulary=tag_vocabulary,
        )
        comp_by_ci[ci] = comp
        scs_by_ci[ci] = scs_rows

    # Reassemble in original manifest order.
    all_sentence_cut_rows: list[dict] = []
    new_components = []
    for ci, _canvas in enumerate(manifest.canvases):
        new_components.append(comp_by_ci[ci])
        all_sentence_cut_rows.extend(scs_by_ci[ci])

    template["BizSpeechComponent"] = json.dumps(
        new_components, ensure_ascii=False, separators=(",", ":")
    )
    template["SentenceCutSpeech"] = json.dumps(
        all_sentence_cut_rows, ensure_ascii=False, separators=(",", ":")
    )
    return template, canvas_uuid_by_name


def _build_component(
    canvas: Canvas,
    canvas_index: int,
    canvas_uuid: str,
    manifest: Manifest,
    minter: IdMinter,
    base: dict[str, Any],
    speech_id: int,
    branch_intent_ids: dict[str, int],
    kb_ids: list[str],
    node_language: str,
    component_nav: list[dict] | None = None,
    canvas_uuid_by_name: dict[str, str] | None = None,
    var_source_by_name: dict[str, int] | None = None,
    nested_exit_map: dict[str, dict[str, str]] | None = None,
    parent_uuid: str = "0",
    mr_target_names: set[str] | None = None,
    kb_name_to_id: dict[str, int] | None = None,
    tag_vocabulary=None,
) -> tuple[dict[str, Any], list[dict]]:
    """Build a single BizSpeechComponent entry using render_component_nodes.

    Returns (component_dict, sentence_cut_speech_rows).
    """
    node_specs = []
    for n in canvas.nodes:
        cfg = dict(n.config)
        if n.type == "goto" and canvas_uuid_by_name:
            # Resolve config.target (a canvas name) to the pre-minted componentUuid.
            target_name = cfg.get("target", "")
            cfg["target_uuid"] = canvas_uuid_by_name.get(target_name, "")
            cfg["target_name"] = target_name
        elif n.type == "goto_mr" and canvas_uuid_by_name:
            # Resolve config.target (a multi-round canvas name) to the pre-minted componentUuid.
            # Target must be a multi-round component (in mr_target_names).
            target_name = cfg.get("target", "")
            if not (mr_target_names and target_name in mr_target_names):
                mr_list = sorted(mr_target_names or [])
                raise ValueError(
                    f"goto_mr node {n.id!r} in canvas {canvas.name!r}: "
                    f"config.target {target_name!r} is not a multi-round dialogue canvas "
                    f"(must be some knowledge_base's multi_round target; known: {mr_list})"
                )
            # Container constraint: the goto_mr node must itself be in a multi-round canvas
            if not (mr_target_names and canvas.name in mr_target_names):
                mr_list = sorted(mr_target_names or [])
                raise ValueError(
                    f"goto_mr node {n.id!r} is in canvas {canvas.name!r} which is not "
                    f"a multi-round dialogue; goto_mr is only valid inside a multi-round component "
                    f"(known multi-round: {mr_list})"
                )
            cfg["target_uuid"] = canvas_uuid_by_name.get(target_name, "")
            if not cfg["target_uuid"]:
                raise ValueError(
                    f"goto_mr node {n.id!r} in canvas {canvas.name!r}: "
                    f"config.target {target_name!r} matches no canvas "
                    f"(known: {sorted(canvas_uuid_by_name.keys())})"
                )
            cfg["target_name"] = target_name
        elif n.type == "talk_continue" and canvas_uuid_by_name:
            # Container constraint: talk_continue must be in a multi-round canvas
            if not (mr_target_names and canvas.name in mr_target_names):
                mr_list = sorted(mr_target_names or [])
                raise ValueError(
                    f"talk_continue node {n.id!r} is in canvas {canvas.name!r} which is "
                    f"not a multi-round dialogue; talk_continue is only valid inside a "
                    f"multi-round component (known multi-round: {mr_list})"
                )
            # Optional return target: resolve to a main-flow (non-MR) component.
            target_name = cfg.get("target", "")
            if target_name:
                if target_name not in canvas_uuid_by_name:
                    raise ValueError(
                        f"talk_continue node {n.id!r} in canvas {canvas.name!r}: "
                        f"config.target {target_name!r} matches no canvas "
                        f"(known: {sorted(canvas_uuid_by_name.keys())})"
                    )
                if mr_target_names and target_name in mr_target_names:
                    mr_list = sorted(mr_target_names or [])
                    raise ValueError(
                        f"talk_continue node {n.id!r} in canvas {canvas.name!r}: "
                        f"return target {target_name!r} is a multi-round component; "
                        f"talk_continue return target must be a main-flow (non-multi-round) canvas "
                        f"(known multi-round: {mr_list})"
                    )
                cfg["target_uuid"] = canvas_uuid_by_name.get(target_name, "")
                cfg["target_name"] = target_name
        elif n.type == "goto_kb":
            # Resolve config.target (a KB name) to the knowledgeId int.
            target_kb_name = cfg.get("target", "")
            target_kid = (kb_name_to_id or {}).get(target_kb_name)
            if target_kid is None:
                raise ValueError(
                    f"goto_kb node {n.id!r} in canvas {canvas.name!r}: "
                    f"config.target {target_kb_name!r} matches no KB "
                    f"(known: {sorted((kb_name_to_id or {}).keys())})"
                )
            cfg["target_kid"] = target_kid
        elif n.type == "nested" and canvas_uuid_by_name:
            # Resolve config.target (a child canvas name) to the pre-minted componentUuid.
            target_name = cfg.get("target", "")
            cfg["target_uuid"] = canvas_uuid_by_name.get(target_name, "")
        node_specs.append(NodeSpec(id=n.id, prompt=n.prompt, type=n.type, config=cfg, tags=n.tags))
    edge_specs = [EdgeSpec(src=e.src, branch=e.branch, dst=e.dst) for e in canvas.edges]

    r = render_component_nodes(
        node_specs,
        edge_specs,
        canvas_index=canvas_index,
        comp_uuid=canvas_uuid,
        speech_id=speech_id,
        branch_intent_ids=branch_intent_ids,
        kb_ids=kb_ids,
        node_language=node_language,
        minter=minter,
        component_nav=component_nav,
        var_source_by_name=var_source_by_name,
        nested_exit_map=nested_exit_map,
        tag_vocabulary=tag_vocabulary,
    )

    # Lay out node positions (data.top/left) so the component doesn't import
    # as a stack at the origin in the WIZ canvas.
    assign_positions(r.details, r.routes)

    entry = {
        "componentUuid": canvas_uuid,
        "name": canvas.name,
        "branch": manifest.branch,
        # category 2 = Multi-Round Dialogue component; 1 = normal Main Talk-Flow. A canvas
        # named as some KB's multi_round target must be filed under the Multi-Round tab.
        "category": 2 if (mr_target_names and canvas.name in mr_target_names)
        else base.get("category", 1),
        "type": base.get("type", 1),
        "language": base.get("language", 0),
        "editStatus": base.get("editStatus", 1),
        "useStatus": base.get("useStatus", 1),
        "parentUuid": parent_uuid,
        "sortIndex": canvas_index + 1,
        "speechId": speech_id,
        "templateCode": base.get("templateCode", ""),
        "createBy": base.get("createBy", 0),
        "updateBy": base.get("updateBy", 0),
        "createTime": base.get("createTime", 0),
        "updateTime": base.get("updateTime", 0),
        "id": minter.int_id(f"component-id:{canvas_index}"),
        "inboundPorts": json.dumps(r.inbound_ports, ensure_ascii=False, separators=(",", ":")),
        "outboundPorts": "[]",
        "routes": json.dumps(r.routes, ensure_ascii=False, separators=(",", ":")),
        "nluConf": "{}",
        "sourceUuid": "",
        # topFloorDetails: one row per exit (type 2) node; empty list for talk-only canvases.
        # Transfer (type 13) nodes do NOT contribute a row (confirmed by fixture 26).
        "topFloorDetails": json.dumps(
            r.top_floor_details, ensure_ascii=False, separators=(",", ":")
        ),
        "details": json.dumps(r.details, ensure_ascii=False, separators=(",", ":")),
    }

    if canvas_index > 0:
        for key in _SECONDARY_STRIP_KEYS:
            entry.pop(key, None)

    return entry, r.sentence_cut_speech
