import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agents
from tools import registry

# A minimal in-memory export with one empty component (index 0).
# componentUuid must be a valid UUID — the checker's parser enforces this.
DATA = {
    "BizSpeechComponent": [{"componentUuid": "00000000-0000-0000-0000-000000000001",
                            "name": "Main", "speechId": 1,
                            "details": "null", "routes": "{}", "inboundPorts": "[]"}],
    "SpeechIntent": [{"intentName": n, "intentId": i} for i, n in
                     enumerate(["Positive", "Negative", "Reject", "Unclassified", "No answer"], 1)],
    "BizKnowledgeInfo": [],
}


@pytest.fixture(scope="module")
def two_component_doc():
    """A 2-component doc built via propose_scaffold (deterministic UUIDs)."""
    params = {
        "name": "Test Bot", "language": "IDN", "branch": "dev",
        "canvases": [
            {"name": "1. Greeting", "nodes": [{"id": "open", "prompt": "Halo"}]},
            {"name": "2. Next", "nodes": [{"id": "open2", "prompt": "Lanjut"}]},
        ],
    }
    r = agents.propose_scaffold(params)
    assert r["ok"], r.get("error")
    return r["proposed_data"]


def test_tools_registered():
    names = [s.name for s in registry.tool_specs()]
    assert "add_component" in names
    assert "add_node" in names


def test_add_node_returns_proposal():
    out = registry.dispatch("add_node", {"component": 0, "id": "g", "prompt": "Greeting"}, DATA)
    assert out["result"]["ok"] is True
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_add_component_returns_proposal():
    out = registry.dispatch("add_component", {"name": "Greeting"}, DATA)
    assert out["result"]["ok"] is True
    assert out["proposal"] is not None


def _decode(data, key):
    """Decode a packed JSON string or return list/dict as-is."""
    v = data.get(key, "[]")
    if isinstance(v, str):
        return json.loads(v)
    return v


def test_add_node_goto_with_config(two_component_doc):
    """add_node with type=goto + config.target resolves to the target component's UUID."""
    bsc = _decode(two_component_doc, "BizSpeechComponent")
    comp1_uuid = bsc[1]["componentUuid"]
    comp1_name = bsc[1]["name"]  # "2. Next"

    # Find the entry node uuid in comp0 (is_default=True)
    comp0_details = json.loads(bsc[0]["details"]) if isinstance(bsc[0]["details"], str) else {}
    entry_uuid = next(uid for uid, obj in comp0_details.items()
                      if (obj.get("data") or {}).get("is_default"))

    res = registry.dispatch("add_node", {
        "component": 0,
        "id": "jump",
        "prompt": "(goto)",
        "type": "goto",
        "config": {"target": comp1_name},
        "edges": [{"from": entry_uuid, "branch": "Unclassified", "to": "jump"}],
    }, two_component_doc)

    assert res["result"]["ok"] is True, res["result"].get("error")
    proposed = res["proposal"]["proposed_data"]
    bsc2 = _decode(proposed, "BizSpeechComponent")
    details2 = json.loads(bsc2[0]["details"])

    # Find the new goto node (type 4) — raw envelope uses obj["type"], not obj["data"]["node_type"]
    goto_nodes = [(uid, obj) for uid, obj in details2.items() if obj.get("type") == 4]
    assert goto_nodes, "No type-4 (goto) node found in proposed comp0"
    assert len(goto_nodes) == 1, f"Expected exactly 1 goto node, got {len(goto_nodes)}"
    _, goto_obj = goto_nodes[0]
    assert goto_obj["data"]["appoint_node_id"] == comp1_uuid
    # Verify component_nav is populated (props.list non-empty proves I-1 fixed)
    props_list = (goto_obj.get("canvas") or {}).get("component", {}).get("props", {}).get("list", [])
    assert props_list, "goto node canvas.component.props.list is empty (append_node missing component_nav)"


def test_connect_components(two_component_doc):
    """connect_components adds a type-4 goto node wired from a source node to a target component."""
    bsc = _decode(two_component_doc, "BizSpeechComponent")
    comp1_uuid = bsc[1]["componentUuid"]
    comp1_name = bsc[1]["name"]  # "2. Next"

    # Find the entry node uuid in comp0 (is_default=True)
    comp0_details = json.loads(bsc[0]["details"]) if isinstance(bsc[0]["details"], str) else {}
    entry_uuid = next(uid for uid, obj in comp0_details.items()
                      if (obj.get("data") or {}).get("is_default"))

    res = registry.dispatch("connect_components", {
        "component": 0,
        "id": "jumpB",
        "target": comp1_name,
        "from": entry_uuid,
        "branch": "Unclassified",
    }, two_component_doc)

    assert res["result"]["ok"] is True, res["result"].get("error")
    proposed = res["proposal"]["proposed_data"]
    bsc2 = _decode(proposed, "BizSpeechComponent")
    details2 = json.loads(bsc2[0]["details"])

    # Find the new goto node (type 4)
    goto_nodes = [(uid, obj) for uid, obj in details2.items() if obj.get("type") == 4]
    assert goto_nodes, "No type-4 (goto) node found in proposed comp0"
    assert len(goto_nodes) == 1, f"Expected exactly 1 goto node, got {len(goto_nodes)}"
    _, goto_obj = goto_nodes[0]
    assert goto_obj["data"]["appoint_node_id"] == comp1_uuid


_EXPECTED_NODE_TYPES = {"talk", "exit", "transfer", "goto", "goto_mr", "conditional", "assign",
                        "nested", "exit_port", "goto_kb"}


# ---------------------------------------------------------------------------
# Task 6 (KB-T6): add_kb tool + scaffold_bot knowledge_bases
# ---------------------------------------------------------------------------

def test_add_kb_tool_registered():
    """tool_specs() must include a tool named add_kb."""
    specs = {s.name: s for s in registry.tool_specs()}
    assert "add_kb" in specs, "add_kb tool not found in registry"


def test_add_kb_tool_schema():
    """add_kb schema exposes name/intents/answers/multi_round."""
    specs = {s.name: s for s in registry.tool_specs()}
    params = specs["add_kb"].parameters
    props = params["properties"]
    assert "name" in props
    assert "intents" in props
    assert props["intents"]["type"] == "array"
    assert "answers" in props
    assert props["answers"]["type"] == "array"
    assert "multi_round" in props
    # name and intents must be required
    assert "name" in params.get("required", [])
    assert "intents" in params.get("required", [])


def test_scaffold_bot_schema_has_knowledge_bases():
    """scaffold_bot schema must include a knowledge_bases property."""
    specs = {s.name: s for s in registry.tool_specs()}
    sb_props = specs["scaffold_bot"].parameters["properties"]
    assert "knowledge_bases" in sb_props, "scaffold_bot schema missing knowledge_bases"
    kb_schema = sb_props["knowledge_bases"]
    assert kb_schema["type"] == "array"
    item_props = kb_schema["items"]["properties"]
    assert "name" in item_props
    assert "intents" in item_props
    assert "answers" in item_props
    assert "multi_round" in item_props


def test_add_kb_dispatch_returns_proposal(two_component_doc):
    """dispatch add_kb builds an add-kb op and returns a proposal.

    Uses two_component_doc (built via scaffold_bot) because the add-kb modifier
    requires BizKnowledgeInfo to have baseline entries to clone config from.
    """
    out = registry.dispatch("add_kb", {
        "name": "FAQ",
        "intents": ["Positive"],
        "answers": ["Yes, we can help."],
    }, two_component_doc)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def _assert_free_string_branch(branch_schema: dict, spec_name: str) -> None:
    """Assert edge branch is a free string (no enum — nested exit-port names are arbitrary)."""
    assert "enum" not in branch_schema, (
        f"{spec_name} edge branch must not have an enum (nested exit-port names are free strings); "
        f"found: {branch_schema.get('enum')}"
    )
    assert branch_schema["type"] == "string", (
        f"{spec_name} edge branch type must be 'string', got {branch_schema['type']!r}"
    )


def test_node_type_enum_includes_conditional_and_assign():
    specs = {s.name: s for s in registry.tool_specs()}

    # --- add_node ---
    props = specs["add_node"].parameters["properties"]
    assert set(props["type"]["enum"]) == _EXPECTED_NODE_TYPES
    # config advertises branches for conditional authoring + name/target for nested/exit_port
    cfg = props["config"]["properties"]
    assert "branches" in cfg and "variable" in cfg and "value" in cfg
    assert "target" in cfg, "add_node config must advertise 'target' (for nested + goto)"
    assert "name" in cfg, "add_node config must advertise 'name' (for exit_port label)"
    # edge branch is a free string — no enum (nested outgoing edges use arbitrary exit-port names)
    _assert_free_string_branch(props["edges"]["items"]["properties"]["branch"], "add_node")

    # --- add_component ---
    ac_props = specs["add_component"].parameters["properties"]
    assert set(ac_props["nodes"]["items"]["properties"]["type"]["enum"]) == _EXPECTED_NODE_TYPES
    ac_cfg = ac_props["nodes"]["items"]["properties"]["config"]["properties"]
    assert "target" in ac_cfg, "add_component config must advertise 'target'"
    assert "name" in ac_cfg, "add_component config must advertise 'name'"
    _assert_free_string_branch(
        ac_props["edges"]["items"]["properties"]["branch"], "add_component"
    )

    # --- scaffold_bot (nodes+edges nested under canvases.items.properties) ---
    sb_canvas_item_props = specs["scaffold_bot"].parameters["properties"]["canvases"]["items"]["properties"]
    sb_node_type_enum = sb_canvas_item_props["nodes"]["items"]["properties"]["type"]["enum"]
    assert set(sb_node_type_enum) == _EXPECTED_NODE_TYPES, (
        f"scaffold_bot node type enum: {sb_node_type_enum}"
    )
    sb_cfg = sb_canvas_item_props["nodes"]["items"]["properties"]["config"]["properties"]
    assert "target" in sb_cfg, "scaffold_bot config must advertise 'target'"
    assert "name" in sb_cfg, "scaffold_bot config must advertise 'name'"
    _assert_free_string_branch(
        sb_canvas_item_props["edges"]["items"]["properties"]["branch"], "scaffold_bot"
    )


def test_scaffold_bot_node_type_enum_includes_goto_kb():
    """scaffold_bot node type enum must include goto_kb (Task 4)."""
    specs = {s.name: s for s in registry.tool_specs()}
    sb_canvas_item_props = (
        specs["scaffold_bot"].parameters["properties"]["canvases"]["items"]["properties"]
    )
    node_type_enum = sb_canvas_item_props["nodes"]["items"]["properties"]["type"]["enum"]
    assert "goto_kb" in node_type_enum, (
        f"scaffold_bot node type enum missing 'goto_kb'; found: {node_type_enum}"
    )


def test_scaffold_bot_node_type_enum_includes_goto_mr():
    """scaffold_bot node type enum must include goto_mr (Task 5)."""
    specs = {s.name: s for s in registry.tool_specs()}
    sb_canvas_item_props = (
        specs["scaffold_bot"].parameters["properties"]["canvases"]["items"]["properties"]
    )
    node_type_enum = sb_canvas_item_props["nodes"]["items"]["properties"]["type"]["enum"]
    assert "goto_mr" in node_type_enum, (
        f"scaffold_bot node type enum missing 'goto_mr'; found: {node_type_enum}"
    )
    # Verify that config.target is documented for goto_mr
    sb_cfg = sb_canvas_item_props["nodes"]["items"]["properties"]["config"]["properties"]
    assert "target" in sb_cfg, "scaffold_bot config must advertise 'target' for goto_mr"


def test_add_node_exit_no_config(two_component_doc):
    """add_node with type=exit (no config) produces a type-2 node."""
    bsc = _decode(two_component_doc, "BizSpeechComponent")
    comp0_details = json.loads(bsc[0]["details"]) if isinstance(bsc[0]["details"], str) else {}
    entry_uuid = next(uid for uid, obj in comp0_details.items()
                      if (obj.get("data") or {}).get("is_default"))

    res = registry.dispatch("add_node", {
        "component": 0,
        "id": "bye",
        "prompt": "Selamat tinggal",
        "type": "exit",
        "edges": [{"from": entry_uuid, "branch": "Unclassified", "to": "bye"}],
    }, two_component_doc)

    assert res["result"]["ok"] is True, res["result"].get("error")
    proposed = res["proposal"]["proposed_data"]
    bsc2 = _decode(proposed, "BizSpeechComponent")
    details2 = json.loads(bsc2[0]["details"])

    # Raw envelope uses obj["type"], not obj["data"]["node_type"]
    exit_nodes = [obj for obj in details2.values() if obj.get("type") == 2]
    assert exit_nodes, "No type-2 (exit) node found in proposed comp0"


# ---------------------------------------------------------------------------
# Task 9 (FM-T9): six flow-mutation chat tools
# ---------------------------------------------------------------------------

_FLOW_MUTATION_TOOLS = [
    "rewire_edge", "delete_edge", "delete_node", "move_node", "rename_node",
    "complete_component",
]

_NODE_REF_SCHEMA = {
    "type": "object",
    "properties": {"uuid": {"type": "string"}, "label": {"type": "string"}},
}


def test_flow_mutation_tools_registered():
    """tool_specs() must include all six flow-mutation tools."""
    names = {s.name for s in registry.tool_specs()}
    for tool_name in _FLOW_MUTATION_TOOLS:
        assert tool_name in names, f"{tool_name!r} not found in registry"


def test_flow_mutation_tool_schemas():
    """Each flow-mutation tool must have the correct parameter schema."""
    specs = {s.name: s for s in registry.tool_specs()}

    # rewire_edge: component(int), from(node-ref), branch(str), to?(node-ref), to_component?(str)
    rw = specs["rewire_edge"].parameters
    assert rw["properties"]["component"]["type"] == "integer"
    assert rw["properties"]["from"] == _NODE_REF_SCHEMA
    assert rw["properties"]["branch"]["type"] == "string"
    assert rw["properties"]["to"] == _NODE_REF_SCHEMA
    assert rw["properties"]["to_component"]["type"] == "string"
    assert set(rw["required"]) >= {"component", "from", "branch"}

    # delete_edge: component(int), from(node-ref), branch(str)
    de = specs["delete_edge"].parameters
    assert de["properties"]["component"]["type"] == "integer"
    assert de["properties"]["from"] == _NODE_REF_SCHEMA
    assert de["properties"]["branch"]["type"] == "string"
    assert set(de["required"]) >= {"component", "from", "branch"}

    # delete_node: component(int), node(node-ref)
    dn = specs["delete_node"].parameters
    assert dn["properties"]["component"]["type"] == "integer"
    assert dn["properties"]["node"] == _NODE_REF_SCHEMA
    assert set(dn["required"]) >= {"component", "node"}

    # move_node: node(node-ref), to_component(str), from_component?(int)
    mn = specs["move_node"].parameters
    assert mn["properties"]["node"] == _NODE_REF_SCHEMA
    assert mn["properties"]["to_component"]["type"] == "string"
    assert "from_component" in mn["properties"]
    assert set(mn["required"]) >= {"node", "to_component"}

    # rename_node: component(int), node(node-ref), label?(str), prompt?(str)
    rn = specs["rename_node"].parameters
    assert rn["properties"]["component"]["type"] == "integer"
    assert rn["properties"]["node"] == _NODE_REF_SCHEMA
    assert rn["properties"]["label"]["type"] == "string"
    assert rn["properties"]["prompt"]["type"] == "string"
    assert set(rn["required"]) >= {"component", "node"}

    # complete_component: component(int), exit_target?(node-ref)
    cc = specs["complete_component"].parameters
    assert cc["properties"]["component"]["type"] == "integer"
    assert cc["properties"]["exit_target"] == _NODE_REF_SCHEMA
    assert set(cc["required"]) >= {"component"}


def test_complete_component_dispatch_returns_proposal(two_component_doc):
    """dispatch complete_component builds a complete-component op and returns a proposal."""
    out = registry.dispatch("complete_component", {"component": 0}, two_component_doc)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_rewire_edge_dispatch_returns_proposal(two_component_doc):
    """dispatch rewire_edge builds a rewire-edge op and returns a proposal.

    After complete_component ensures there is an exit node, rewire_edge
    re-targets the entry node's Unclassified branch to that same exit node.
    """
    # First complete component 0 so it has an exit node + wired branches.
    completed = registry.dispatch("complete_component", {"component": 0}, two_component_doc)
    assert completed["result"]["ok"] is True, completed["result"].get("error")
    doc_with_exit = completed["proposal"]["proposed_data"]

    bsc = _decode(doc_with_exit, "BizSpeechComponent")
    details0 = json.loads(bsc[0]["details"])
    entry_uuid = next(uid for uid, obj in details0.items()
                      if (obj.get("data") or {}).get("is_default"))
    exit_uuid = next(uid for uid, obj in details0.items() if obj.get("type") == 2)

    out = registry.dispatch("rewire_edge", {
        "component": 0,
        "from": {"uuid": entry_uuid},
        "branch": "Unclassified",
        "to": {"uuid": exit_uuid},
    }, doc_with_exit)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None


def test_complete_component_op_dict():
    """complete_component with component=0 (no exit_target) builds the minimal op dict.

    We verify the proposal is generated (end-to-end), which implicitly validates the
    op dict sent to propose_mods contains op='complete-component' and component=0.
    """
    out = registry.dispatch("complete_component", {"component": 0}, DATA)
    # DATA has one empty component at index 0; complete_component should succeed.
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
