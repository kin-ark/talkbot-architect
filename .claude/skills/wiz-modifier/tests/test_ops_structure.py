import sys
from pathlib import Path

import pytest

# wiz-builder's scripts dir is a sibling skill, not on pythonpath.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "wiz-builder" / "scripts")
)

from wizbuilder.ids import IdMinter  # noqa: E402
from wizmodifier import codec  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops import content, structure  # noqa: E402
from wizmodifier.ops._bsc import get_components  # noqa: E402

MINTER = IdMinter(manifest_hash="deadbeef")


def test_add_bsc_keys_defaults(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    structure.add_bsc_keys(b, {"component": 0}, MINTER)
    comp = get_components(b)[0]
    for k, v in {
        "inboundPorts": "[]", "outboundPorts": "[]", "routes": "[]",
        "nluConf": "{}", "sourceUuid": "", "topFloorDetails": "[]",
    }.items():
        assert comp[k] == v


def test_populate_details_builds_envelope(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "n1", "prompt": "Greeting"}]},
        MINTER,
    )
    comp = get_components(b)[0]
    details = codec.decode(comp["details"])
    node_obj = next(iter(details.values()))
    # New real node shape: top-level has canvas + data keys (not props.list)
    assert "data" in node_obj
    assert node_obj["data"]["dialog_list"][0]["text"] == "Greeting"
    assert "canvas" in node_obj


def test_add_component_appends_entry(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    before = len(get_components(b))
    structure.add_component(b, {"name": "Second Canvas"}, MINTER)
    comps = get_components(b)
    assert len(comps) == before + 1
    new = comps[-1]
    assert new["name"] == "Second Canvas"
    assert new["details"] == "null"  # no nodes given
    assert new["parentUuid"] == "0"
    assert new["sortIndex"] == before + 1


def test_add_component_with_nodes_populates_details(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    structure.add_component(
        b,
        {"name": "Flow", "nodes": [{"id": "root", "prompt": "Open"}]},
        MINTER,
    )
    new = get_components(b)[-1]
    assert new["details"] != "null"
    details = codec.decode(new["details"])
    node_obj = next(iter(details.values()))
    # New real node shape: top-level has data key
    assert "data" in node_obj
    assert node_obj["data"]["dialog_list"][0]["text"] == "Open"


def test_add_component_strips_template_keys_from_secondary(baseline_dict):
    """Secondary components (index>0) must not carry template-only and first-comp-only keys."""
    _KEYS_TO_STRIP = {"createBy", "createTime", "language", "nluConf", "outboundPorts", "updateBy"}

    b = InputBundle(data=baseline_dict, speech_name="s.json")

    # Ensure baseline component 0 has at least some of these keys (it inherits from template)
    comps_before = get_components(b)
    comp0_keys = set(comps_before[0].keys())
    # Skip test if baseline doesn't have any of these keys (already clean)
    if not (_KEYS_TO_STRIP & comp0_keys):
        pytest.skip("baseline has none of the expected strippable keys")

    structure.add_component(b, {"name": "2. Canvas"}, MINTER)

    comps = get_components(b)
    comp1_keys = set(comps[1].keys())
    leaked = _KEYS_TO_STRIP & comp1_keys
    assert not leaked, (
        f"secondary component should not have template-only keys, but found: {leaked}"
    )


def test_append_node_assign_wired_via_default_port(baseline_dict):
    """Append an assign node (type 10) whose 'Default' out-port is wired to an existing talk node.

    The assign builder bakes a single out-port named 'Default'; the normal edges loop (no
    special handling needed) must wire it to the downstream target.
    """
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    content.add_variable(b, {"name": "DEBT_AMT", "branch": "dev"}, MINTER)

    # First populate component 0 with a talk node so we have an existing node to wire to.
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "talk1", "prompt": "How much do you owe?"}]},
        MINTER,
    )
    comp = get_components(b)[0]
    talk_uuid = next(iter(codec.decode(comp["details"])))

    # Append an assign node as a NEW ENTRY NODE; its 'Default' out-port routes to talk1.
    # The assign node is the source (logical id "assign1"), talk node is the destination.
    structure.append_node(
        b,
        {
            "component": 0,
            "node": {
                "id": "assign1",
                "prompt": "",
                "type": "assign",
                "config": {"variable": "DEBT_AMT", "value": "500000"},
            },
            "edges": [{"from": "assign1", "branch": "Default", "to": talk_uuid}],
        },
        MINTER,
    )

    comp = get_components(b)[0]
    details = codec.decode(comp["details"])
    routes = codec.decode(comp["routes"])

    # Locate the new assign node (type 10).
    assign_objs = {k: v for k, v in details.items() if v.get("type") == 10}
    assert len(assign_objs) == 1, "expected exactly one assign node"
    assign_uuid, assign_obj = next(iter(assign_objs.items()))
    assert assign_obj["data"]["value_assignment"][0]["assign"]["params"][0]["value"] == "500000"

    # The assign node's 'Default' port must be wired to the existing talk node.
    assign_routes = routes.get(assign_uuid, {})
    assert any(
        v["target"]["uuid"] == talk_uuid for v in assign_routes.values()
    ), "assign node 'Default' port should route to the existing talk node"


def test_append_node_conditional_branch_routes(baseline_dict):
    """Append a conditional node (type 7) whose branches point at an existing talk node uuid.

    routes[cond_uuid] must have one entry per distinct branch name, and every target uuid
    must be the existing talk node's uuid.
    """
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    content.add_variable(b, {"name": "DEBT_AMT", "branch": "dev"}, MINTER)

    # Populate component 0 with a talk node; its uuid will be the branch target.
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "talk1", "prompt": "Collecting debt info"}]},
        MINTER,
    )
    comp = get_components(b)[0]
    talk_uuid = next(iter(codec.decode(comp["details"])))

    # Real operator tokens (">", "<=") — the 11-op set the validator enforces.
    branches = [
        {"name": "High", "op": ">", "value": "100000", "to": talk_uuid},
        {"name": "Low", "op": "<=", "value": "100000", "to": talk_uuid},
        {"name": "Default", "to": talk_uuid},
    ]
    structure.append_node(
        b,
        {
            "component": 0,
            "node": {
                "id": "cond1",
                "prompt": "",
                "type": "conditional",
                "config": {"variable": "DEBT_AMT", "branches": branches},
            },
            "edges": [],
        },
        MINTER,
    )

    comp = get_components(b)[0]
    details = codec.decode(comp["details"])
    routes = codec.decode(comp["routes"])

    cond_objs = {k: v for k, v in details.items() if v.get("type") == 7}
    assert len(cond_objs) == 1, "expected exactly one conditional node"
    cond_uuid = next(iter(cond_objs))
    cond_obj = cond_objs[cond_uuid]

    # The conditional node's all_client_intent ids are the route keys.
    aci_ids = {entry["id"] for entry in cond_obj["data"]["all_client_intent"]}
    cond_routes = routes.get(cond_uuid, {})
    assert set(cond_routes.keys()) == aci_ids, (
        f"routes keys {set(cond_routes.keys())} should equal all_client_intent ids {aci_ids}"
    )

    # Every route target must be the existing talk node.
    for port_uuid, route in cond_routes.items():
        assert route["target"]["uuid"] == talk_uuid, (
            f"port {port_uuid}: expected target {talk_uuid}, got {route['target']['uuid']}"
        )


def test_append_node_conditional_rejects_invalid_op(baseline_dict):
    """A conditional branch with an operator not in the 11-op set must raise ValueError."""
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    content.add_variable(b, {"name": "DEBT_AMT", "branch": "dev"}, MINTER)
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "talk1", "prompt": "Collecting debt info"}]},
        MINTER,
    )
    talk_uuid = next(iter(codec.decode(get_components(b)[0]["details"])))
    branches = [
        {"name": "High", "op": "GT", "value": "100000", "to": talk_uuid},  # invalid token
        {"name": "Default", "to": talk_uuid},
    ]
    with pytest.raises(ValueError, match="invalid operator"):
        structure.append_node(
            b,
            {
                "component": 0,
                "node": {
                    "id": "cond1",
                    "prompt": "",
                    "type": "conditional",
                    "config": {"variable": "DEBT_AMT", "branches": branches},
                },
                "edges": [],
            },
            MINTER,
        )


def test_add_variable_rejects_duplicate_name(baseline_dict):
    """add_variable must raise on a name already present in SpeechVariable (SPEECH-0230)."""
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    content.add_variable(b, {"name": "user_name", "branch": "dev"}, MINTER)
    with pytest.raises(ValueError, match="already exists"):
        content.add_variable(b, {"name": "user_name", "branch": "dev"}, MINTER)


# ---------------------------------------------------------------------------
# Nested + exit_port tests (NC-T4)
# ---------------------------------------------------------------------------


def test_add_component_with_exit_port_nodes(baseline_dict):
    """add_component for a child canvas with exit_port nodes emits type-4 terminal nodes
    with empty appoint_node_id and specificComponentName (the exit_port discriminant).
    """
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    structure.add_component(
        b,
        {
            "name": "Child Canvas",
            "nodes": [
                {"id": "talk1", "prompt": "Child intro"},
                {
                    "id": "ep1",
                    "prompt": "",
                    "type": "exit_port",
                    "config": {"name": "Done"},
                },
            ],
            "edges": [{"from": "talk1", "branch": "Positive", "to": "ep1"}],
        },
        MINTER,
    )
    child_comp = get_components(b)[-1]
    assert child_comp["name"] == "Child Canvas"
    details = codec.decode(child_comp["details"])

    # Find exit_port node: type 4 with empty appoint_node_id + specificComponentName.
    exit_port_objs = {
        k: v for k, v in details.items()
        if v.get("type") == 4
        and v.get("data", {}).get("appoint_node_id", "") == ""
        and v.get("data", {}).get("specificComponentName", "") == ""
    }
    assert len(exit_port_objs) == 1, "expected exactly one exit_port node"
    ep_uuid, ep_obj = next(iter(exit_port_objs.items()))
    assert ep_obj["data"]["name"] == "Done"

    # topFloorDetails must contain the exit_port's data dict.
    tfd = codec.decode(child_comp["topFloorDetails"])
    assert isinstance(tfd, list)
    assert any(row.get("name") == "Done" for row in tfd), (
        "topFloorDetails must carry the exit_port data row"
    )


def test_append_node_nested_mirrors_child_exit_ports(baseline_dict):
    """append_node a nested node targeting a child component: the nested node's routes
    are keyed by the child's exit-port node UUIDs (matching the builder's wiring).
    """
    b = InputBundle(data=baseline_dict, speech_name="s.json")

    # Step 1: add a child canvas with one exit_port node.
    structure.add_component(
        b,
        {
            "name": "Child Canvas",
            "nodes": [
                {"id": "ep1", "prompt": "", "type": "exit_port", "config": {"name": "Done"}},
            ],
        },
        MINTER,
    )
    child_comp = get_components(b)[-1]
    child_details = codec.decode(child_comp["details"])
    # Locate the child exit_port uuid.
    child_exit_uuid = next(
        uuid for uuid, obj in child_details.items()
        if obj.get("type") == 4
        and obj.get("data", {}).get("appoint_node_id", "") == ""
    )

    # Step 2: populate the parent component (index 0) with a talk node.
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "root", "prompt": "Root talk"}]},
        MINTER,
    )
    comp0 = get_components(b)[0]
    root_uuid = next(iter(codec.decode(comp0["details"])))

    # Step 3: append a nested node into the parent, wiring its "Done" port to root.
    structure.append_node(
        b,
        {
            "component": 0,
            "node": {
                "id": "nested1",
                "prompt": "",
                "type": "nested",
                "config": {"target": "Child Canvas"},
            },
            "edges": [{"from": "nested1", "branch": "Done", "to": root_uuid}],
        },
        MINTER,
    )

    comp0 = get_components(b)[0]
    details = codec.decode(comp0["details"])
    routes = codec.decode(comp0["routes"])

    # Find the nested node (type 11).
    nested_objs = {k: v for k, v in details.items() if v.get("type") == 11}
    assert len(nested_objs) == 1, "expected exactly one nested node"
    nested_uuid = next(iter(nested_objs))

    # routes[nested_uuid] must be keyed by the child's exit_port uuid.
    nested_routes = routes.get(nested_uuid, {})
    assert child_exit_uuid in nested_routes, (
        f"routes[nested] must be keyed by child exit uuid {child_exit_uuid!r}; "
        f"got keys {list(nested_routes.keys())}"
    )
    assert nested_routes[child_exit_uuid]["target"]["uuid"] == root_uuid


def test_append_node_nested_target_no_exit_port_raises(baseline_dict):
    """append_node a nested node whose target child has NO exit_port nodes must raise ValueError."""
    b = InputBundle(data=baseline_dict, speech_name="s.json")

    # Add a child canvas with only a talk node (no exit_port).
    structure.add_component(
        b,
        {
            "name": "Empty Child",
            "nodes": [{"id": "talk1", "prompt": "Just a talk node"}],
        },
        MINTER,
    )

    # Populate parent with a talk node so append_node has something to target.
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "root", "prompt": "Root"}]},
        MINTER,
    )
    comp0 = get_components(b)[0]
    root_uuid = next(iter(codec.decode(comp0["details"])))

    with pytest.raises(ValueError, match="exit_port"):
        structure.append_node(
            b,
            {
                "component": 0,
                "node": {
                    "id": "nested1",
                    "prompt": "",
                    "type": "nested",
                    "config": {"target": "Empty Child"},
                },
                "edges": [{"from": "nested1", "branch": "Done", "to": root_uuid}],
            },
            MINTER,
        )


def test_append_node_nested_envelope_id_and_source_type_3(baseline_dict):
    """FIX 1 + FIX 2: appended nested node must have envelope id == subComponentUuid,
    and its route out-edges must have source.type == 3 (not 1).

    FIX 1: Without the envelope id, WIZ import returns code:-1.
    FIX 2: With source.type=1 the import succeeds but the deployed flow is broken.
    """
    b = InputBundle(data=baseline_dict, speech_name="s.json")

    # Step 1: add a child canvas with one exit_port node.
    structure.add_component(
        b,
        {
            "name": "Child Canvas",
            "nodes": [
                {"id": "ep1", "prompt": "", "type": "exit_port", "config": {"name": "Done"}},
            ],
        },
        MINTER,
    )
    child_comp = get_components(b)[-1]
    child_comp_uuid = child_comp["componentUuid"]
    child_details = codec.decode(child_comp["details"])
    child_exit_uuid = next(
        uuid for uuid, obj in child_details.items()
        if obj.get("type") == 4 and obj.get("data", {}).get("appoint_node_id", "") == ""
    )

    # Step 2: populate the parent component (index 0) with a talk node.
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "root", "prompt": "Root talk"}]},
        MINTER,
    )
    comp0 = get_components(b)[0]
    root_uuid = next(iter(codec.decode(comp0["details"])))

    # Step 3: append the nested node with a "Done" out-edge to root.
    structure.append_node(
        b,
        {
            "component": 0,
            "node": {
                "id": "nested1",
                "prompt": "",
                "type": "nested",
                "config": {"target": "Child Canvas"},
            },
            "edges": [{"from": "nested1", "branch": "Done", "to": root_uuid}],
        },
        MINTER,
    )

    comp0 = get_components(b)[0]
    details = codec.decode(comp0["details"])
    routes = codec.decode(comp0["routes"])

    nested_objs = {k: v for k, v in details.items() if v.get("type") == 11}
    assert len(nested_objs) == 1, "expected exactly one nested node"
    nested_uuid, nested_obj = next(iter(nested_objs.items()))

    # FIX 1: top-level 'id' must equal the child component's UUID (subComponentUuid).
    assert "id" in nested_obj, "nested node_obj must have a top-level 'id' key"
    assert nested_obj["id"] == child_comp_uuid, (
        f"nested node envelope id must == child componentUuid {child_comp_uuid!r}, "
        f"got {nested_obj.get('id')!r}"
    )

    # FIX 2: the out-route for the nested node must have source.type == 3.
    nested_routes = routes.get(nested_uuid, {})
    assert child_exit_uuid in nested_routes, (
        f"nested route must be keyed by child exit uuid {child_exit_uuid!r}"
    )
    edge_obj = nested_routes[child_exit_uuid]
    assert edge_obj["source"]["type"] == 3, (
        f"nested out-edge source.type must be 3, got {edge_obj['source']['type']!r}"
    )


def test_append_node_exit_port_with_outgoing_edge_raises(baseline_dict):
    """append_node an exit_port node with an outgoing edge must raise ValueError
    (exit_port is terminal and must not have outgoing edges).
    """
    b = InputBundle(data=baseline_dict, speech_name="s.json")

    # Populate the component with a talk node so we have an existing uuid to wire to.
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "root", "prompt": "Root"}]},
        MINTER,
    )
    comp0 = get_components(b)[0]
    root_uuid = next(iter(codec.decode(comp0["details"])))

    with pytest.raises(ValueError, match="terminal"):
        structure.append_node(
            b,
            {
                "component": 0,
                "node": {
                    "id": "ep1",
                    "prompt": "",
                    "type": "exit_port",
                    "config": {"name": "Done"},
                },
                # exit_port cannot have outgoing edges
                "edges": [{"from": "ep1", "branch": "Positive", "to": root_uuid}],
            },
            MINTER,
        )
