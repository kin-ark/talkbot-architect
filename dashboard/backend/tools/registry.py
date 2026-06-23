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
    ToolSpec("scaffold_bot",
             "Create a brand-new dialogue from typed parameters (NOT raw YAML). "
             "Proposes a full new doc (dry-run). Use after the user confirms an outline.",
             {"type": "object",
              "properties": {
                  "name": {"type": "string"},
                  "language": {"type": "string", "enum": ["ENG", "IDN", "ZHO", "THA"]},
                  "branch": {"type": "string", "enum": ["dev", "prod"]},
                  "custom_variables": {"type": "array", "items": {
                      "type": "object", "properties": {"name": {"type": "string"}},
                      "required": ["name"]}},
                  "custom_intents": {"type": "array", "items": {
                      "type": "object", "properties": {
                          "name": {"type": "string"},
                          "language": {"type": "string", "enum": ["ENG", "IDN", "ZHO", "THA"]},
                          "keywords": {"type": "array", "items": {"type": "string"}},
                          "user_responses": {"type": "array", "items": {"type": "string"}}},
                      "required": ["name", "language"]}},
                  "canvases": {"type": "array", "items": {
                      "type": "object", "properties": {
                          "name": {"type": "string"},
                          "nodes": {"type": "array", "items": {
                              "type": "object", "properties": {
                                  "id": {"type": "string"}, "prompt": {"type": "string"}},
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
    return {"result": {"error": f"unknown tool {name!r}"}, "proposal": None}


def _as_proposal(p: dict) -> dict:
    if not p.get("ok"):
        return {"result": {"ok": False, "error": p.get("error"),
                           "known_ops": p.get("known_ops")}, "proposal": None}
    return {"result": {"ok": True, "diff": p["diff"], "checker_delta": p["checker_delta"]},
            "proposal": {"proposed_data": p["proposed_data"], "diff": p["diff"],
                         "checker_delta": p["checker_delta"]}}
