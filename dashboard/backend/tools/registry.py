# tools/registry.py
from __future__ import annotations

import agents
from llm.base import ToolSpec

_SPECS = [
    ToolSpec("validate", "Run the WIZ checker on the current dialogue. Returns findings.",
             {"type": "object", "properties": {}}),
    ToolSpec("summarize", "Return the dialogue flow model (components, nodes, branches, KBs).",
             {"type": "object", "properties": {}}),
    ToolSpec("read_node", "Read one flow node's full detail by uuid.",
             {"type": "object", "properties": {"uuid": {"type": "string"}}, "required": ["uuid"]}),
    ToolSpec("get_facts", "Look up WIZ.AI product facts by keyword.",
             {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
    ToolSpec("apply_mods",
             "Propose edits via modifier ops (YAML list of {op, ...}). Dry-run: returns a diff "
             "and checker delta; nothing is committed until the user applies.",
             {"type": "object", "properties": {"mods_yaml": {"type": "string"}},
              "required": ["mods_yaml"]}),
    ToolSpec("set_path",
             "Escape-hatch edit: set a value at a dotted/indexed path in the export. Proposes only.",
             {"type": "object", "properties": {"path": {"type": "string"}, "value": {}},
              "required": ["path", "value"]}),
    ToolSpec("delete_path", "Escape-hatch edit: delete the value at a path. Proposes only.",
             {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}),
    ToolSpec("build", "Scaffold a brand-new dialogue from a manifest YAML. Proposes a full new doc.",
             {"type": "object", "properties": {"manifest_yaml": {"type": "string"}},
              "required": ["manifest_yaml"]}),
    ToolSpec("get_schema",
             "Return the manifest schema, known node labels, and modifier op names. "
             "Call this before authoring scaffold_bot params or ops.",
             {"type": "object", "properties": {}}),
    ToolSpec("scaffold_bot",
             "Create a brand-new dialogue from typed parameters (NOT raw YAML). "
             "Proposes a full new doc (dry-run). Use after the user confirms an outline. "
             "languages: ENG, IDN (ZHO/THA pending verified language codes). "
             "Each node may include an optional type (talk/exit/transfer/goto/conditional/assign/"
             "nested/exit_port/goto_kb; default: talk). goto nodes require config.target set to "
             "the name of another canvas to jump to. nested nodes delegate to a child canvas "
             "(config.target = child canvas name); their outgoing edges branch on the child "
             "canvas's exit_port names. exit_port is a named terminal return inside a child canvas "
             "(config.name = the port label). conditional nodes route by config.variable + "
             "config.branches (each {name, op, value|value_var, to}); assign nodes set "
             "config.variable to config.value. goto_kb is a terminal jump into a Knowledge Base "
             "(config.target = a KB name). "
             "Optionally declare knowledge_bases (each has a name, triggering intents list, "
             "answer(s), and optional multi_round = a canvas name to delegate multi-turn Q&A into).",
             {"type": "object",
              "properties": {
                  "name": {"type": "string"},
                  "language": {"type": "string", "enum": ["ENG", "IDN"]},
                  "branch": {"type": "string", "enum": ["dev", "prod"]},
                  "custom_variables": {"type": "array", "items": {
                      "type": "object", "properties": {"name": {"type": "string"}},
                      "required": ["name"]}},
                  "custom_intents": {"type": "array", "items": {
                      "type": "object", "properties": {
                          "name": {"type": "string"},
                          "language": {"type": "string", "enum": ["ENG", "IDN"]},
                          "keywords": {"type": "array", "items": {"type": "string"}},
                          "user_responses": {"type": "array", "items": {"type": "string"}}},
                      "required": ["name", "language"]}},
                  "knowledge_bases": {"type": "array", "items": {
                      "type": "object", "properties": {
                          "name": {"type": "string"},
                          "intents": {"type": "array", "items": {"type": "string"}},
                          "answers": {"type": "array", "items": {"type": "string"}},
                          "multi_round": {"type": "string"}},
                      "required": ["name", "intents"]}},
                  "canvases": {"type": "array", "items": {
                      "type": "object", "properties": {
                          "name": {"type": "string"},
                          "nodes": {"type": "array", "items": {
                              "type": "object", "properties": {
                                  "id": {"type": "string"},
                                  "prompt": {"type": "string"},
                                  "type": {"type": "string",
                                           "enum": ["talk", "exit", "transfer", "goto",
                                                    "conditional", "assign",
                                                    "nested", "exit_port", "goto_kb"]},
                                  "config": {"type": "object", "properties": {
                                      "target": {"type": "string"},
                                      "name": {"type": "string"},
                                      "variable": {"type": "string"},
                                      "value": {"type": "string"},
                                      "branches": {"type": "array", "items": {
                                          "type": "object", "properties": {
                                              "name": {"type": "string"},
                                              "op": {"type": "string",
                                                     "enum": [">", ">=", "<", "<=", "=", "!=",
                                                              "In", "NotIn", "IsNull", "NotNull",
                                                              "Contains"]},
                                              "value": {"type": "string"},
                                              "value_var": {"type": "string"},
                                              "to": {"type": "string"}},
                                          "required": ["name", "to"]}}}}},
                              "required": ["id", "prompt"]}},
                          "edges": {"type": "array", "items": {
                              "type": "object", "properties": {
                                  "from": {"type": "string"},
                                  "branch": {"type": "string", "minLength": 1},
                                  "to": {"type": "string"}},
                              "required": ["from", "branch", "to"]}}},
                      "required": ["name", "nodes"]}},
              },
              "required": ["name", "language", "branch", "canvases"]}),
    ToolSpec("add_component",
             "Add a new component (optionally with nodes+edges) to the current dialogue. Proposes a dry-run. "
             "Each node may include an optional type (talk/exit/transfer/goto/conditional/assign/"
             "nested/exit_port/goto_kb; default: talk). "
             "goto nodes require config.target set to the name of another component to jump to. "
             "nested nodes delegate to a child canvas (config.target = child canvas name); their "
             "outgoing edges branch on the child canvas's exit_port names. exit_port is a named "
             "terminal return inside a child canvas (config.name = the port label). "
             "conditional nodes route by config.variable + config.branches (each {name, op, value|value_var, to}); "
             "assign nodes set config.variable to config.value. "
             "goto_kb is a terminal jump into a Knowledge Base (config.target = a KB name).",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "nodes": {"type": "array", "items": {"type": "object", "properties": {
                     "id": {"type": "string"},
                     "prompt": {"type": "string"},
                     "type": {"type": "string", "enum": ["talk", "exit", "transfer", "goto",
                                                         "conditional", "assign",
                                                         "nested", "exit_port", "goto_kb"]},
                     "config": {"type": "object", "properties": {
                         "target": {"type": "string"},
                         "name": {"type": "string"},
                         "variable": {"type": "string"},
                         "value": {"type": "string"},
                         "branches": {"type": "array", "items": {
                             "type": "object", "properties": {
                                 "name": {"type": "string"},
                                 "op": {"type": "string",
                                        "enum": [">", ">=", "<", "<=", "=", "!=",
                                                 "In", "NotIn", "IsNull", "NotNull", "Contains"]},
                                 "value": {"type": "string"},
                                 "value_var": {"type": "string"},
                                 "to": {"type": "string"}},
                             "required": ["name", "to"]}}}}},
                     "required": ["id", "prompt"]}},
                 "edges": {"type": "array", "items": {"type": "object", "properties": {
                     "from": {"type": "string"},
                     "branch": {"type": "string", "minLength": 1},
                     "to": {"type": "string"}}, "required": ["from", "branch", "to"]}}},
              "required": ["name"]}),
    ToolSpec("add_node",
             "Add a node (talk/exit/transfer/goto/conditional/assign/nested/exit_port/goto_kb) to an existing "
             "component (by index), optionally wiring edges. Edge endpoints: the new node's id, or an "
             "existing node's uuid. goto requires config.target = another component's name. "
             "nested delegates to a child canvas (config.target = child canvas name); outgoing edges "
             "branch on the child canvas's exit_port names (free strings, not an enum). "
             "exit_port is a named terminal return inside a child canvas (config.name = port label). "
             "conditional nodes route by config.variable + config.branches (each {name, op, value|value_var, to}). "
             "assign nodes set config.variable to config.value; assign continue-edges use branch: \"Default\". "
             "goto_kb is a terminal jump into a Knowledge Base (config.target = a KB name). "
             "Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "id": {"type": "string"},
                 "prompt": {"type": "string"},
                 "type": {"type": "string", "enum": ["talk", "exit", "transfer", "goto",
                                                     "conditional", "assign",
                                                     "nested", "exit_port", "goto_kb"]},
                 "config": {"type": "object", "properties": {
                     "target": {"type": "string"},
                     "name": {"type": "string"},
                     "variable": {"type": "string"},
                     "value": {"type": "string"},
                     "branches": {"type": "array", "items": {
                         "type": "object", "properties": {
                             "name": {"type": "string"},
                             "op": {"type": "string",
                                    "enum": [">", ">=", "<", "<=", "=", "!=",
                                             "In", "NotIn", "IsNull", "NotNull", "Contains"]},
                             "value": {"type": "string"},
                             "value_var": {"type": "string"},
                             "to": {"type": "string"}},
                         "required": ["name", "to"]}}}},
                 "edges": {"type": "array", "items": {"type": "object", "properties": {
                     "from": {"type": "string"},
                     "branch": {"type": "string", "minLength": 1},
                     "to": {"type": "string"}}, "required": ["from", "branch", "to"]}}},
              "required": ["component", "id", "prompt"]}),
    ToolSpec("connect_components",
             "Add a goto_component node that jumps from one component to another "
             "(cross-component link). Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "id": {"type": "string"},
                 "target": {"type": "string"},
                 "from": {"type": "string"},
                 "branch": {"type": "string",
                            "enum": ["Positive", "Negative", "Reject", "Unclassified", "No answer"]},
                 "prompt": {"type": "string"}},
              "required": ["component", "id", "target", "from", "branch"]}),
    ToolSpec("add_intent",
             "Add a custom intent to the dialogue. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "language": {"type": "string", "enum": ["ENG", "IDN"]},
                 "keywords": {"type": "array", "items": {"type": "string"}}},
              "required": ["name", "language"]}),
    ToolSpec("add_variable",
             "Add a custom variable to the dialogue. Proposes a dry-run.",
             {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}),
    ToolSpec("add_kb",
             "Add a Knowledge Base (triggering intents + answer(s); optional multi_round = a "
             "canvas/component name to delegate into). Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "intents": {"type": "array", "items": {"type": "string"}},
                 "answers": {"type": "array", "items": {"type": "string"}},
                 "multi_round": {"type": "string"}},
              "required": ["name", "intents"]}),
    ToolSpec("rename_kb",
             "Rename an existing Knowledge Base. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "new_name": {"type": "string"}},
              "required": ["name", "new_name"]}),
    ToolSpec("set_kb_intents",
             "Replace the triggering intents of a Knowledge Base. "
             "Each intent name must already exist in SpeechIntent. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "intents": {"type": "array", "items": {"type": "string"}}},
              "required": ["name", "intents"]}),
    ToolSpec("add_kb_answer",
             "Append a new answer text to a Knowledge Base. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "text": {"type": "string"}},
              "required": ["name", "text"]}),
    ToolSpec("edit_kb_answer",
             "Edit an existing answer in a Knowledge Base, located by old_text or 0-based index. "
             "Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "new_text": {"type": "string"},
                 "old_text": {"type": "string"},
                 "index": {"type": "integer"}},
              "required": ["name", "new_text"]}),
    ToolSpec("remove_kb_answer",
             "Remove an answer from a Knowledge Base, located by text or 0-based index. "
             "The KB must keep at least one response. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "text": {"type": "string"},
                 "index": {"type": "integer"}},
              "required": ["name"]}),
    ToolSpec("set_kb_multiround",
             "Set or remove multi-round delegation for a Knowledge Base. "
             "Pass target_component = a canvas/component name to enable, or null to remove. "
             "Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "target_component": {"type": ["string", "null"]}},
              "required": ["name"]}),
    ToolSpec("delete_kb",
             "Delete a user-created Knowledge Base (isInit=0). "
             "Refuses if the KB is referenced by goto_kb nodes. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"}},
              "required": ["name"]}),
    ToolSpec("rewire_edge",
             "Set or replace an edge route for a branch on a node. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "from": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}},
                 "branch": {"type": "string"},
                 "to": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}},
                 "to_component": {"type": "string"}},
              "required": ["component", "from", "branch"]}),
    ToolSpec("delete_edge",
             "Remove the route for a branch on a node (leaves the out-port intact). Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "from": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}},
                 "branch": {"type": "string"}},
              "required": ["component", "from", "branch"]}),
    ToolSpec("delete_node",
             "Remove a node and cascade-clean all related tables. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "node": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}}},
              "required": ["component", "node"]}),
    ToolSpec("move_node",
             "Move a node from one component to another. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "node": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}},
                 "to_component": {"type": "string"},
                 "from_component": {"type": "integer"}},
              "required": ["node", "to_component"]}),
    ToolSpec("rename_node",
             "Set a new label and/or prompt text on a node. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "node": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}},
                 "label": {"type": "string"},
                 "prompt": {"type": "string"}},
              "required": ["component", "node"]}),
    ToolSpec("complete_component",
             "Auto-complete a component to WIZ completeness rules (exit node + wired branches). "
             "Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "exit_target": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}}},
              "required": ["component"]}),
]


def tool_specs() -> list[ToolSpec]:
    return list(_SPECS)


def dispatch(name: str, args: dict, data: dict) -> dict:
    if name == "validate":
        return {"result": agents.validate(data), "proposal": None}
    if name == "summarize":
        return {"result": agents.summarize(data), "proposal": None}
    if name == "read_node":
        return {"result": agents.read_node(data, args["uuid"]), "proposal": None}
    if name == "get_facts":
        return {"result": agents.get_facts(args["query"]), "proposal": None}
    if name == "apply_mods":
        p = agents.propose_mods(data, args["mods_yaml"])
        return _as_proposal(p)
    if name == "set_path":
        import yaml
        mods = yaml.safe_dump([{"op": "set-path", "path": args["path"], "value": args["value"]}])
        return _as_proposal(agents.propose_mods(data, mods))
    if name == "delete_path":
        import yaml
        mods = yaml.safe_dump([{"op": "delete-path", "path": args["path"]}])
        return _as_proposal(agents.propose_mods(data, mods))
    if name == "build":
        built = agents.propose_build(args["manifest_yaml"])
        if not built["ok"]:
            return {"result": {"ok": False, "error": built["error"]}, "proposal": None}
        import yaml as _yaml
        import speechname as _sn
        try:
            _mani = _yaml.safe_load(args["manifest_yaml"])
            _nm = _mani.get("name") if isinstance(_mani, dict) else None
        except Exception:
            _nm = None
        if _nm:
            built["proposed_data"] = _sn.set_speech_name(built["proposed_data"], _nm)
        # Enrich via propose_scaffold path: compute summary/change_set from the built doc
        after_summary = agents.summarize(built["proposed_data"])
        import proposal_meta as _pm
        empty_summary = {"components": [], "knowledge_bases": []}
        cs = _pm.change_set(empty_summary, after_summary)
        p = {"ok": True, "proposed_data": built["proposed_data"],
             "diff": "(new dialogue scaffolded)", "checker_delta": None,
             "proposed_summary": after_summary, "change_set": cs,
             "change_summary": _pm.change_summary(cs, None)}
        return _as_proposal(p)
    if name == "scaffold_bot":
        p = agents.propose_scaffold(args)
        if p.get("ok") and args.get("name"):
            import speechname as _sn
            p["proposed_data"] = _sn.set_speech_name(p["proposed_data"], args["name"])
        return _as_proposal(p)
    if name == "get_schema":
        return {"result": agents.get_schema(), "proposal": None}
    if name == "add_component":
        import yaml
        op = {"op": "add-component", "name": args["name"]}
        if args.get("nodes"):
            op["nodes"] = args["nodes"]
        if args.get("edges"):
            op["edges"] = args["edges"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "add_node":
        import yaml
        node = {"id": args["id"], "prompt": args["prompt"]}
        if args.get("type"):
            node["type"] = args["type"]
        if args.get("config"):
            node["config"] = args["config"]
        op = {"op": "append-node", "component": args["component"], "node": node}
        if args.get("edges"):
            op["edges"] = args["edges"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "add_intent":
        import yaml
        op = {"op": "add-intent", "name": args["name"], "language": args["language"]}
        if args.get("keywords"):
            op["keywords"] = args["keywords"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "add_variable":
        import yaml
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump(
            [{"op": "add-variable", "name": args["name"]}])))
    if name == "add_kb":
        import yaml
        op = {"op": "add-kb", "name": args["name"], "intents": args["intents"],
              "answers": args.get("answers", [])}
        if args.get("multi_round"):
            op["multi_round"] = args["multi_round"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "rename_kb":
        import yaml
        op = {"op": "rename-kb", "name": args["name"], "new_name": args["new_name"]}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "set_kb_intents":
        import yaml
        op = {"op": "set-kb-intents", "name": args["name"], "intents": args["intents"]}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "add_kb_answer":
        import yaml
        op = {"op": "add-kb-answer", "name": args["name"], "text": args["text"]}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "edit_kb_answer":
        import yaml
        op = {"op": "edit-kb-answer", "name": args["name"], "new_text": args["new_text"]}
        if args.get("old_text") is not None:
            op["old_text"] = args["old_text"]
        if args.get("index") is not None:
            op["index"] = args["index"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "remove_kb_answer":
        import yaml
        op = {"op": "remove-kb-answer", "name": args["name"]}
        if args.get("text") is not None:
            op["text"] = args["text"]
        if args.get("index") is not None:
            op["index"] = args["index"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "set_kb_multiround":
        import yaml
        op = {"op": "set-kb-multiround", "name": args["name"],
              "target_component": args.get("target_component")}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "delete_kb":
        import yaml
        op = {"op": "delete-kb", "name": args["name"]}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "connect_components":
        import yaml
        node = {"id": args["id"], "prompt": args.get("prompt", "(goto)"),
                "type": "goto", "config": {"target": args["target"]}}
        op = {"op": "append-node", "component": args["component"], "node": node,
              "edges": [{"from": args["from"], "branch": args["branch"], "to": args["id"]}]}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "rewire_edge":
        import yaml
        op = {"op": "rewire-edge", "component": args["component"],
              "from": args["from"], "branch": args["branch"]}
        if args.get("to"):
            op["to"] = args["to"]
        if args.get("to_component"):
            op["to_component"] = args["to_component"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "delete_edge":
        import yaml
        op = {"op": "delete-edge", "component": args["component"],
              "from": args["from"], "branch": args["branch"]}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "delete_node":
        import yaml
        op = {"op": "delete-node", "component": args["component"], "node": args["node"]}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "move_node":
        import yaml
        op = {"op": "move-node", "node": args["node"], "to_component": args["to_component"]}
        if args.get("from_component") is not None:
            op["from_component"] = args["from_component"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "rename_node":
        import yaml
        op = {"op": "rename-node", "component": args["component"], "node": args["node"]}
        if args.get("label"):
            op["label"] = args["label"]
        if args.get("prompt"):
            op["prompt"] = args["prompt"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    if name == "complete_component":
        import yaml
        op = {"op": "complete-component", "component": args["component"]}
        if args.get("exit_target"):
            op["exit_target"] = args["exit_target"]
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    return {"result": {"error": f"unknown tool {name!r}"}, "proposal": None}


def _as_proposal(p: dict) -> dict:
    if not p.get("ok"):
        return {"result": {"ok": False, "error": p.get("error"),
                           "known_ops": p.get("known_ops")}, "proposal": None}
    proposal = {"proposed_data": p["proposed_data"], "diff": p["diff"],
                "checker_delta": p["checker_delta"]}
    for k in ("proposed_summary", "change_set", "change_summary"):
        if k in p:
            proposal[k] = p[k]
    findings = agents.validate(p["proposed_data"])
    proposal["findings"] = findings
    result = {"ok": True, "diff": p["diff"], "checker_delta": p["checker_delta"],
              "change_summary": p.get("change_summary")}
    if findings:
        result["findings"] = findings
    return {"result": result, "proposal": proposal}
