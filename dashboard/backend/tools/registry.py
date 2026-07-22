# tools/registry.py
from __future__ import annotations

import yaml

import agents
from llm.base import ToolSpec

_SPECS = [
    ToolSpec("validate", "Run the WIZ checker on the current dialogue. Returns findings.",
             {"type": "object", "properties": {}}),
    ToolSpec("summarize", "Return the dialogue flow model (components, nodes, branches, KBs).",
             {"type": "object", "properties": {}}),
    ToolSpec("read_node", "Read one flow node's full detail by uuid.",
             {"type": "object", "properties": {"uuid": {"type": "string"}}, "required": ["uuid"]}),
    ToolSpec("list_intents",
             "List the dialogue's intents (name + whether user-created + whether it lacks NLU signal). "
             "Call before add_intent / before authoring a KB trigger to avoid duplicates.",
             {"type": "object", "properties": {}}),
    ToolSpec("list_variables",
             "List the dialogue's variables (name + source: system|custom). Call before add_variable "
             "or before a conditional to see what already exists.",
             {"type": "object", "properties": {}}),
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
    ToolSpec("get_playbook",
             "Retrieve a corpus-derived blueprint (flow skeleton, stage tuning, "
             "intents, KBs, scripts) for a known bot vertical, e.g. 'debt_collection'. "
             "Call this BEFORE scaffolding a whole new bot in that domain.",
             {"type": "object",
              "properties": {"vertical": {"type": "string"}},
              "required": ["vertical"]}),
    ToolSpec("list_samples",
             "List available starter-bot sample manifests (id, title, description). "
             "Descriptions name the debt-collection STAGE (Predue/DPD0/DPD1-5/DPD6-30/"
             "Overdue90/PTP). Use this to pick the closest sample to seed a new bot.",
             {"type": "object", "properties": {}}),
    ToolSpec("get_sample",
             "Return a sample's FULL manifest YAML. ADAPT it (brand, customer amounts/dates, "
             "stage tone) and pass it to `build` — prefer this over composing scaffold_bot "
             "from scratch whenever a sample matches the requested vertical/stage.",
             {"type": "object", "properties": {"sample_id": {"type": "string"}},
              "required": ["sample_id"]}),
    ToolSpec("get_debt_corpus",
             "Query the debt-collection corpus (real-frequency, prevalence-ranked). Returns up "
             "to top_n (<=30) ranked items for a section, to enrich/verify a scaffold.",
             {"type": "object",
              "properties": {
                  "section": {"type": "string",
                              "enum": ["intents", "kbs", "script_archetypes", "flow_engines",
                                       "stage_deltas", "objection_map", "tag_patterns"]},
                  "stage": {"type": "string"},
                  "top_n": {"type": "integer"}},
              "required": ["section"]}),
    ToolSpec("scaffold_bot",
             "Create a brand-new dialogue from typed parameters (NOT raw YAML). "
             "Proposes a full new doc (dry-run). Use after the user confirms an outline. "
             "languages: ENG, IDN (ZHO/THA pending verified language codes). "
             "Each node may include an optional type (talk/exit/transfer/goto/goto_mr/talk_continue/conditional/assign/"
             "nested/exit_port/goto_kb; default: talk). goto nodes require config.target set to "
             "the name of another canvas to jump to. goto_mr is an exit node that jumps to a multi-round dialogue component: "
             "config.target = another canvas name (must be a multi-round target; terminal). "
             "talk_continue: speak-and-wait response node; ONLY inside a multi-round (category:2) component; optional config.target = a main-flow component to return to; terminal, no speech-audio. "
             "nested nodes delegate to a child canvas (config.target = child canvas name); their outgoing edges branch on the child "
             "canvas's exit_port names. exit_port is a named terminal return inside a child canvas "
             "(config.name = the port label). conditional nodes route by config.variable + "
             "config.branches (each {name, op, value|value_var, to}); assign nodes set "
             "config.variable to config.value. goto_kb is a terminal jump into a Knowledge Base "
             "(config.target = a KB name). "
             "Optionally declare knowledge_bases (each has a name, triggering intents list, "
             "answer(s), and optional multi_round = a canvas name to delegate multi-turn Q&A into). "
             "Optionally declare disposition tags (top-level categories: [{name, values}]) and tag nodes "
             "(per-node: [{category, values}]).",
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
                  "tags": {"type": "array", "items": {"type": "object",
                      "properties": {"name": {"type": "string"},
                                     "values": {"type": "array", "items": {"type": "string"}}},
                      "required": ["name", "values"]}},
                  "canvases": {"type": "array", "items": {
                      "type": "object", "properties": {
                          "name": {"type": "string"},
                          "nodes": {"type": "array", "items": {
                              "type": "object", "properties": {
                                  "id": {"type": "string"},
                                  "prompt": {"type": "string"},
                                  "type": {"type": "string",
                                           "enum": ["talk", "exit", "transfer", "goto", "goto_mr",
                                                    "talk_continue", "conditional", "assign",
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
                                          "required": ["name", "to"]}},
                                      "branch_intents": {
                                          "type": "object",
                                          "additionalProperties": {
                                              "type": "array", "items": {"type": "string"}}}}}},
                                  "tags": {"type": "array", "items": {"type": "object",
                                      "properties": {"category": {"type": "string"},
                                                     "values": {"type": "array", "items": {"type": "string"}}},
                                      "required": ["category", "values"]}},
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
             "Each node may include an optional type (talk/exit/transfer/goto/goto_mr/talk_continue/conditional/assign/"
             "nested/exit_port/goto_kb; default: talk). "
             "goto nodes require config.target set to the name of another component to jump to. "
             "goto_mr is an exit node that jumps to a multi-round dialogue component: config.target = another component name (must be a multi-round target; terminal). "
             "talk_continue: speak-and-wait response node; ONLY inside a multi-round (category:2) component; optional config.target = a main-flow component to return to; terminal, no speech-audio. "
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
                     "type": {"type": "string", "enum": ["talk", "exit", "transfer", "goto", "goto_mr",
                                                         "talk_continue", "conditional", "assign",
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
             "Add a node (talk/exit/transfer/goto/goto_mr/talk_continue/conditional/assign/nested/exit_port/goto_kb) to an existing "
             "component (by index), optionally wiring edges. Edge endpoints: the new node's id, or an "
             "existing node's uuid. goto requires config.target = another component's name. "
             "goto_mr is an exit node that jumps to a multi-round dialogue component: config.target = another component's name (must be a multi-round target; terminal). "
             "talk_continue: speak-and-wait response node; ONLY inside a multi-round (category:2) component; optional config.target = a main-flow component to return to; terminal, no speech-audio. "
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
                 "type": {"type": "string", "enum": ["talk", "exit", "transfer", "goto", "goto_mr",
                                                     "talk_continue", "conditional", "assign",
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
                 "branch": {"type": "string", "minLength": 1,
                            "description": "A system branch (Positive/Negative/Reject/Unclassified/"
                                           "'No answer') OR a custom branch_intents label on the source node."},
                 "prompt": {"type": "string"}},
              "required": ["component", "id", "target", "from", "branch"]}),
    ToolSpec("add_intent",
             "Add a custom intent to the dialogue. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "language": {"type": "string", "enum": ["ENG", "IDN"]},
                 "keywords": {"type": "array", "items": {"type": "string"}},
                 "user_responses": {"type": "array", "items": {"type": "string"}}},
              "required": ["name", "language"]}),
    ToolSpec("add_variable",
             "Add a custom variable to the dialogue. Proposes a dry-run.",
             {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}),
    ToolSpec("set_hotwords",
             "Set global hotwords or hotwords on a specific node for NLU training. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "hot_words": {"type": "array", "items": {"type": "string"}},
                 "node": {"type": ["string", "null"]}},
              "required": ["hot_words"]}),
    ToolSpec("set_node_tags",
             "Assign disposition tags (category + values) to a node. Resolves by name against existing tags, "
             "auto-appends absent ones. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "node": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}},
                 "tags": {"type": "array", "items": {"type": "object", "properties": {
                     "category": {"type": "string"},
                     "values": {"type": "array", "items": {"type": "string"}}},
                          "required": ["category", "values"]}}},
              "required": ["node", "tags"]}),
    ToolSpec("set_intent_training",
             "Set training data (keywords and user_responses) for a custom intent. Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "keywords": {"type": "array", "items": {"type": "string"}},
                 "user_responses": {"type": "array", "items": {"type": "string"}}},
              "required": ["name"]}),
    ToolSpec("import_intents_xlsx",
             "Import the intent Excel the user attached this turn into the current bot "
             "(proposal). Call only when the user attached an intent spreadsheet.",
             {"type": "object", "properties": {}}),
    ToolSpec("import_kb_xlsx",
             "Import the KB Excel the user attached this turn into the current bot "
             "(proposal). Call only when the user attached a KB spreadsheet.",
             {"type": "object", "properties": {}}),
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
                 "text": {"type": "string"},
                 "after": {"type": "string", "enum": ["wait", "hangup"],
                          "description": "what happens after the answer: 'wait' (default) or 'hangup'"}},
              "required": ["name", "text"]}),
    ToolSpec("edit_kb_answer",
             "Edit an existing answer in a Knowledge Base, located by old_text or 0-based index. "
             "Proposes a dry-run.",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "new_text": {"type": "string"},
                 "old_text": {"type": "string"},
                 "index": {"type": "integer"},
                 "after": {"type": "string", "enum": ["wait", "hangup"],
                          "description": "what happens after the answer: 'wait' (default) or 'hangup'"}},
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
    ToolSpec("delete_component",
             "Remove a whole component and cascade-clean its rows (sentence cuts, hotwords). "
             "Blocks (no mutation) if it is still referenced by a goto/goto_mr/nested node or a "
             "KB multi-round delegate, or if it has child components — rewire/delete those first. "
             "Proposes a dry-run.",
             {"type": "object", "properties": {"component": {"type": "integer"}},
              "required": ["component"]}),
    ToolSpec("edit_node_config",
             "Retarget or reconfigure an EXISTING node in place (uuid + ports preserved). "
             "Dispatches by the node's current type: goto -> to_component (another component name); "
             "goto_kb -> kb (a Knowledge Base name); goto_mr -> to_component (another multi-round "
             "component name); assign -> variable and/or value; conditional -> variable and/or "
             "branches (each {name, op, value|value_var} — updates the existing branch row matching "
             "name; the branch's out-port is NOT changed). Proposes a dry-run.",
             {"type": "object", "properties": {
                 "component": {"type": "integer"},
                 "node": {"type": "object", "properties": {
                     "uuid": {"type": "string"}, "label": {"type": "string"}}},
                 "to_component": {"type": "string"},
                 "kb": {"type": "string"},
                 "variable": {"type": "string"},
                 "value": {"type": "string"},
                 "branches": {"type": "array", "items": {
                     "type": "object", "properties": {
                         "name": {"type": "string"},
                         "op": {"type": "string",
                                "enum": [">", ">=", "<", "<=", "=", "!=",
                                         "In", "NotIn", "IsNull", "NotNull", "Contains"]},
                         "value": {"type": "string"},
                         "value_var": {"type": "string"}},
                     "required": ["name"]}}},
              "required": ["component", "node"]}),
]


def tool_specs() -> list[ToolSpec]:
    return list(_SPECS)


# --- tool handlers: name -> fn(args, data) -> {"result", "proposal"} ---------
# Registered in _HANDLERS below; dispatch() validates required args then routes.

def _mods(data, op):
    """Common path: dry-run a single modifier op as a proposal."""
    return _as_proposal(agents.propose_mods(data, yaml.safe_dump([op])))


def _h_validate(a, d):
    return {"result": agents.validate(d), "proposal": None}


def _h_summarize(a, d):
    return {"result": agents.summarize(d), "proposal": None}


def _h_read_node(a, d):
    return {"result": agents.read_node(d, a["uuid"]), "proposal": None}


def _h_list_intents(a, d):
    return {"result": agents.list_intents(d), "proposal": None}


def _h_list_variables(a, d):
    return {"result": agents.list_variables(d), "proposal": None}


def _h_get_facts(a, d):
    return {"result": agents.get_facts(a["query"]), "proposal": None}


def _h_get_schema(a, d):
    return {"result": agents.get_schema(), "proposal": None}


def _h_get_playbook(a, d):
    return {"result": agents.get_playbook(a["vertical"]), "proposal": None}


def _h_get_debt_corpus(a, d):
    return {"result": agents.get_debt_corpus(a["section"], a.get("stage"), a.get("top_n", 15)),
            "proposal": None}


def _h_apply_mods(a, d):
    return _as_proposal(agents.propose_mods(d, a["mods_yaml"]))


def _h_set_path(a, d):
    return _mods(d, {"op": "set-path", "path": a["path"], "value": a["value"]})


def _h_delete_path(a, d):
    return _mods(d, {"op": "delete-path", "path": a["path"]})


def _h_list_samples(a, d):
    import samples
    return {"result": samples.list_samples(), "proposal": None}


def _h_get_sample(a, d):
    import samples
    sid = a["sample_id"]
    man = samples.load_manifest(sid)
    if man is None:
        return {"result": {"error": f"unknown sample id: {sid}",
                           "available": [s["id"] for s in samples.list_samples()]},
                "proposal": None}
    return {"result": {"id": sid, "manifest_yaml": man}, "proposal": None}


def _h_build(a, d):
    built = agents.propose_build(a["manifest_yaml"])
    if not built["ok"]:
        return {"result": {"ok": False, "error": built["error"]}, "proposal": None}
    import speechname as _sn
    try:
        _mani = yaml.safe_load(a["manifest_yaml"])
        _nm = _mani.get("name") if isinstance(_mani, dict) else None
    except Exception:
        _nm = None
    if _nm:
        built["proposed_data"] = _sn.set_speech_name(built["proposed_data"], _nm)
    # Enrich via the propose_scaffold path: compute summary/change_set from the built doc.
    after_summary = agents.summarize(built["proposed_data"])
    import proposal_meta as _pm
    empty_summary = {"components": [], "knowledge_bases": []}
    cs = _pm.change_set(empty_summary, after_summary)
    p = {"ok": True, "proposed_data": built["proposed_data"],
         "diff": "(new dialogue scaffolded)", "checker_delta": None,
         "proposed_summary": after_summary, "change_set": cs,
         "change_summary": _pm.change_summary(cs, None)}
    return _as_proposal(p, mature=True)


def _h_scaffold_bot(a, d):
    p = agents.propose_scaffold(a)
    if p.get("ok") and a.get("name"):
        import speechname as _sn
        p["proposed_data"] = _sn.set_speech_name(p["proposed_data"], a["name"])
    return _as_proposal(p, mature=True)


def _h_add_component(a, d):
    op = {"op": "add-component", "name": a["name"]}
    if a.get("nodes"):
        op["nodes"] = a["nodes"]
    if a.get("edges"):
        op["edges"] = a["edges"]
    return _mods(d, op)


def _node_config_error(node: dict) -> str | None:
    """Cheap pre-check mirroring the engine's _validate_special_node for the
    common single-node cases, so a missing type-conditional config fails fast
    instead of after a full propose round-trip. goto_kb/talk_continue targets
    are optional (omitted here); the engine stays the source of truth."""
    t = node.get("type") or "talk"
    cfg = node.get("config") or {}
    need = {
        "goto": ("target",), "goto_mr": ("target",), "nested": ("target",),
        "exit_port": ("name",),
        "conditional": ("variable", "branches"),
        "assign": ("variable", "value"),
    }.get(t)
    if not need:
        return None
    missing = [k for k in need if not cfg.get(k)]
    if missing:
        return (f"node type {t!r} requires config.{', config.'.join(missing)}; "
                "add it and resend.")
    return None


def _h_add_node(a, d):
    node = {"id": a["id"], "prompt": a["prompt"]}
    if a.get("type"):
        node["type"] = a["type"]
    if a.get("config"):
        node["config"] = a["config"]
    err = _node_config_error(node)
    if err:
        return {"result": {"ok": False, "error": err}, "proposal": None}
    op = {"op": "append-node", "component": a["component"], "node": node}
    if a.get("edges"):
        op["edges"] = a["edges"]
    return _mods(d, op)


def _h_add_intent(a, d):
    op = {"op": "add-intent", "name": a["name"], "language": a["language"]}
    if a.get("keywords"):
        op["keywords"] = a["keywords"]
    if a.get("user_responses"):
        op["user_responses"] = a["user_responses"]
    return _mods(d, op)


def _h_add_variable(a, d):
    return _mods(d, {"op": "add-variable", "name": a["name"]})


def _h_set_hotwords(a, d):
    op = {"op": "set-hotwords", "hot_words": a["hot_words"]}
    if a.get("node") is not None:
        op["node"] = a["node"]
    return _mods(d, op)


def _h_set_node_tags(a, d):
    return _mods(d, {"op": "set-node-tags", "node": a["node"], "tags": a["tags"]})


def _h_set_intent_training(a, d):
    op = {"op": "set-intent-training", "name": a["name"]}
    if a.get("keywords"):
        op["keywords"] = a["keywords"]
    if a.get("user_responses"):
        op["user_responses"] = a["user_responses"]
    return _mods(d, op)


def _import_xlsx(a, d, op_name, label):
    path = a.get("path")
    if not path:
        return {"result": {"ok": False, "error": f"no {label} Excel attached this turn"},
                "proposal": None}
    return _mods(d, {"op": op_name, "path": path})


def _h_import_intents_xlsx(a, d):
    return _import_xlsx(a, d, "import-intents-xlsx", "intent")


def _h_import_kb_xlsx(a, d):
    return _import_xlsx(a, d, "import-kb-xlsx", "KB")


def _h_add_kb(a, d):
    op = {"op": "add-kb", "name": a["name"], "intents": a["intents"],
          "answers": a.get("answers", [])}
    if a.get("multi_round"):
        op["multi_round"] = a["multi_round"]
    return _mods(d, op)


def _h_rename_kb(a, d):
    return _mods(d, {"op": "rename-kb", "name": a["name"], "new_name": a["new_name"]})


def _h_set_kb_intents(a, d):
    return _mods(d, {"op": "set-kb-intents", "name": a["name"], "intents": a["intents"]})


def _h_add_kb_answer(a, d):
    op = {"op": "add-kb-answer", "name": a["name"], "text": a["text"]}
    if a.get("after") is not None:
        op["after"] = a["after"]
    return _mods(d, op)


def _h_edit_kb_answer(a, d):
    op = {"op": "edit-kb-answer", "name": a["name"], "new_text": a["new_text"]}
    if a.get("old_text") is not None:
        op["old_text"] = a["old_text"]
    if a.get("index") is not None:
        op["index"] = a["index"]
    if a.get("after") is not None:
        op["after"] = a["after"]
    return _mods(d, op)


def _h_remove_kb_answer(a, d):
    op = {"op": "remove-kb-answer", "name": a["name"]}
    if a.get("text") is not None:
        op["text"] = a["text"]
    if a.get("index") is not None:
        op["index"] = a["index"]
    return _mods(d, op)


def _h_set_kb_multiround(a, d):
    return _mods(d, {"op": "set-kb-multiround", "name": a["name"],
                     "target_component": a.get("target_component")})


def _h_delete_kb(a, d):
    return _mods(d, {"op": "delete-kb", "name": a["name"]})


def _h_connect_components(a, d):
    node = {"id": a["id"], "prompt": a.get("prompt", "(goto)"),
            "type": "goto", "config": {"target": a["target"]}}
    op = {"op": "append-node", "component": a["component"], "node": node,
          "edges": [{"from": a["from"], "branch": a["branch"], "to": a["id"]}]}
    return _mods(d, op)


def _h_rewire_edge(a, d):
    op = {"op": "rewire-edge", "component": a["component"], "from": a["from"], "branch": a["branch"]}
    if a.get("to"):
        op["to"] = a["to"]
    if a.get("to_component"):
        op["to_component"] = a["to_component"]
    return _mods(d, op)


def _h_delete_edge(a, d):
    return _mods(d, {"op": "delete-edge", "component": a["component"],
                     "from": a["from"], "branch": a["branch"]})


def _h_delete_node(a, d):
    return _mods(d, {"op": "delete-node", "component": a["component"], "node": a["node"]})


def _h_move_node(a, d):
    op = {"op": "move-node", "node": a["node"], "to_component": a["to_component"]}
    if a.get("from_component") is not None:
        op["from_component"] = a["from_component"]
    return _mods(d, op)


def _h_rename_node(a, d):
    op = {"op": "rename-node", "component": a["component"], "node": a["node"]}
    if a.get("label"):
        op["label"] = a["label"]
    if a.get("prompt"):
        op["prompt"] = a["prompt"]
    return _mods(d, op)


def _h_complete_component(a, d):
    op = {"op": "complete-component", "component": a["component"]}
    if a.get("exit_target"):
        op["exit_target"] = a["exit_target"]
    return _mods(d, op)


def _h_delete_component(a, d):
    return _mods(d, {"op": "delete-component", "component": a["component"]})


def _h_edit_node_config(a, d):
    op = {"op": "set-node-config", "component": a["component"], "node": a["node"]}
    for k in ("to_component", "kb", "variable", "value", "branches"):
        if a.get(k) is not None:
            op[k] = a[k]
    return _mods(d, op)


_HANDLERS = {
    "validate": _h_validate, "summarize": _h_summarize, "read_node": _h_read_node,
    "list_intents": _h_list_intents, "list_variables": _h_list_variables,
    "get_facts": _h_get_facts, "get_schema": _h_get_schema, "get_playbook": _h_get_playbook,
    "get_debt_corpus": _h_get_debt_corpus, "apply_mods": _h_apply_mods,
    "set_path": _h_set_path, "delete_path": _h_delete_path,
    "list_samples": _h_list_samples, "get_sample": _h_get_sample,
    "build": _h_build, "scaffold_bot": _h_scaffold_bot,
    "add_component": _h_add_component, "add_node": _h_add_node, "add_intent": _h_add_intent,
    "add_variable": _h_add_variable, "set_hotwords": _h_set_hotwords,
    "set_node_tags": _h_set_node_tags, "set_intent_training": _h_set_intent_training,
    "import_intents_xlsx": _h_import_intents_xlsx, "import_kb_xlsx": _h_import_kb_xlsx,
    "add_kb": _h_add_kb, "rename_kb": _h_rename_kb, "set_kb_intents": _h_set_kb_intents,
    "add_kb_answer": _h_add_kb_answer, "edit_kb_answer": _h_edit_kb_answer,
    "remove_kb_answer": _h_remove_kb_answer, "set_kb_multiround": _h_set_kb_multiround,
    "delete_kb": _h_delete_kb, "connect_components": _h_connect_components,
    "rewire_edge": _h_rewire_edge, "delete_edge": _h_delete_edge, "delete_node": _h_delete_node,
    "move_node": _h_move_node, "rename_node": _h_rename_node,
    "complete_component": _h_complete_component,
    "delete_component": _h_delete_component, "edit_node_config": _h_edit_node_config,
}


def dispatch(name: str, args: dict, data: dict) -> dict:
    # A truncated/empty tool call from the model can arrive missing its required
    # args. Guard here so a missing key returns a clean error the model can act
    # on, instead of a raw KeyError that kills the whole turn.
    spec = next((s for s in _SPECS if s.name == name), None)
    if spec is not None:
        missing = [k for k in (spec.parameters or {}).get("required", [])
                   if k not in args or args[k] is None]
        if missing:
            return {"result": {"ok": False,
                               "error": f"missing required argument(s): {', '.join(missing)}. "
                                        "Re-issue the tool call with all required fields."},
                    "proposal": None}
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"result": {"error": f"unknown tool {name!r}"}, "proposal": None}
    return handler(args, data)


def _as_proposal(p: dict, *, mature: bool = False) -> dict:
    if not p.get("ok"):
        return {"result": {"ok": False, "error": p.get("error"),
                           "known_ops": p.get("known_ops")}, "proposal": None}
    proposed_data = p["proposed_data"]
    maturity = None
    # Maturity gate: only auto-mature fresh builds/scaffolds
    if mature:
        proposed_data, maturity = agents.ensure_mature(p["proposed_data"])
    proposal = {"proposed_data": proposed_data, "diff": p["diff"],
                "checker_delta": p["checker_delta"]}
    if maturity is not None:
        proposal["maturity"] = maturity
    for k in ("proposed_summary", "change_set", "change_summary"):
        if k in p:
            proposal[k] = p[k]
    # Validate the data (matured if mature=True, original if False)
    findings = agents.validate(proposed_data)
    proposal["findings"] = findings
    # Attach feature_coverage only on mature builds/scaffolds
    if mature:
        proposal["feature_coverage"] = agents.feature_coverage(proposed_data)
    result = {"ok": True, "diff": p["diff"], "checker_delta": p["checker_delta"],
              "change_summary": p.get("change_summary")}
    if findings:
        result["findings"] = findings
    return {"result": result, "proposal": proposal}
