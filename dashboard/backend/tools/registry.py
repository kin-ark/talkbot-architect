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
             "Each node may include an optional type (talk/exit/transfer/goto; default: talk). "
             "goto nodes require config.target set to the name of another canvas to jump to.",
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
                  "canvases": {"type": "array", "items": {
                      "type": "object", "properties": {
                          "name": {"type": "string"},
                          "nodes": {"type": "array", "items": {
                              "type": "object", "properties": {
                                  "id": {"type": "string"},
                                  "prompt": {"type": "string"},
                                  "type": {"type": "string",
                                           "enum": ["talk", "exit", "transfer", "goto"]},
                                  "config": {"type": "object", "properties": {
                                      "target": {"type": "string"}}}},
                              "required": ["id", "prompt"]}},
                          "edges": {"type": "array", "items": {
                              "type": "object", "properties": {
                                  "from": {"type": "string"},
                                  "branch": {"type": "string",
                                             "enum": ["Positive", "Negative", "Reject",
                                                      "Unclassified", "No answer"]},
                                  "to": {"type": "string"}},
                              "required": ["from", "branch", "to"]}}},
                      "required": ["name", "nodes"]}},
              },
              "required": ["name", "language", "branch", "canvases"]}),
    ToolSpec("add_component",
             "Add a new component (optionally with nodes+edges) to the current dialogue. Proposes a dry-run. "
             "Each node may include an optional type (talk/exit/transfer/goto; default: talk). "
             "goto nodes require config.target set to the name of another component to jump to.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "nodes": {"type": "array", "items": {"type": "object", "properties": {
                     "id": {"type": "string"},
                     "prompt": {"type": "string"},
                     "type": {"type": "string", "enum": ["talk", "exit", "transfer", "goto"]},
                     "config": {"type": "object", "properties": {"target": {"type": "string"}}}},
                     "required": ["id", "prompt"]}},
                 "edges": {"type": "array", "items": {"type": "object", "properties": {
                     "from": {"type": "string"},
                     "branch": {"type": "string", "enum": ["Positive", "Negative", "Reject", "Unclassified", "No answer"]},
                     "to": {"type": "string"}}, "required": ["from", "branch", "to"]}}},
              "required": ["name"]}),
    ToolSpec("add_node",
             "Add a node (talk/exit/transfer/goto) to an existing component (by index), optionally wiring edges. "
             "Edge endpoints: the new node's id, or an existing node's uuid. "
             "goto requires config.target = another component's name. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "id": {"type": "string"},
                 "prompt": {"type": "string"},
                 "type": {"type": "string", "enum": ["talk", "exit", "transfer", "goto"]},
                 "config": {"type": "object", "properties": {"target": {"type": "string"}}},
                 "edges": {"type": "array", "items": {"type": "object", "properties": {
                     "from": {"type": "string"},
                     "branch": {"type": "string", "enum": ["Positive", "Negative", "Reject", "Unclassified", "No answer"]},
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
        p = agents.propose_build(args["manifest_yaml"])
        if not p["ok"]:
            return {"result": {"ok": False, "error": p["error"]}, "proposal": None}
        return {"result": {"ok": True}, "proposal": {"proposed_data": p["proposed_data"],
                "diff": "(new dialogue scaffolded)", "checker_delta": None}}
    if name == "scaffold_bot":
        p = agents.propose_scaffold(args)
        if not p["ok"]:
            return {"result": {"ok": False, "error": p["error"]}, "proposal": None}
        return {"result": {"ok": True, "diff": p["diff"], "checker_delta": p["checker_delta"]},
                "proposal": {"proposed_data": p["proposed_data"],
                             "diff": p["diff"], "checker_delta": p["checker_delta"]}}
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
    if name == "connect_components":
        import yaml
        node = {"id": args["id"], "prompt": args.get("prompt", "(goto)"),
                "type": "goto", "config": {"target": args["target"]}}
        op = {"op": "append-node", "component": args["component"], "node": node,
              "edges": [{"from": args["from"], "branch": args["branch"], "to": args["id"]}]}
        return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))
    return {"result": {"error": f"unknown tool {name!r}"}, "proposal": None}


def _as_proposal(p: dict) -> dict:
    if not p.get("ok"):
        return {"result": {"ok": False, "error": p.get("error"),
                           "known_ops": p.get("known_ops")}, "proposal": None}
    return {"result": {"ok": True, "diff": p["diff"], "checker_delta": p["checker_delta"]},
            "proposal": {"proposed_data": p["proposed_data"], "diff": p["diff"],
                         "checker_delta": p["checker_delta"]}}
