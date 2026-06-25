"""Tests for nested-component (type-11) and exit_port (type-4 disambiguation) reading.

Covers:
  1. Parent component "1. Greeting": the type-11 node reads as node_type=="nested_component"
     with data["subComponentUuid"] set and 3 branches (one per child exit port), each
     branch target_uuid resolving to a parent node.
  2. Child component "Subcomponent1": its 3 type-4 nodes read as node_type=="exit_port"
     (NOT goto_component), each with a terminal kind=="exit" branch; the child's
     parent_uuid equals the parent component's uuid.
  3. A type-4 node with appoint_node_id populated still reads as goto_component
     (disambiguation didn't over-trigger).
"""
import json
from pathlib import Path

import pytest
from wizcheck.flowmodel import _build_node, build_components, node_type_of

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nested_components.json"


@pytest.fixture(scope="module")
def nested_data():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def nested_components(nested_data):
    return build_components(nested_data)


@pytest.fixture(scope="module")
def parent_comp(nested_components):
    """The top-level '1. Greeting' component."""
    return next(c for c in nested_components if c.name == "1. Greeting")


@pytest.fixture(scope="module")
def child_comp(nested_components):
    """The child 'Subcomponent1' component."""
    return next(c for c in nested_components if c.name == "Subcomponent1")


# ---------------------------------------------------------------------------
# 1. Parent component: type-11 node reads as nested_component
# ---------------------------------------------------------------------------

class TestNestedComponentNode:
    def test_type11_node_exists_in_parent(self, parent_comp):
        """Parent component must contain a type-11 node."""
        type11_nodes = [n for n in parent_comp.nodes.values() if n.node_type == "nested_component"]
        assert len(type11_nodes) == 1, (
            f"Expected 1 nested_component node, found {len(type11_nodes)}"
        )

    def test_type11_node_type_name(self, parent_comp):
        """The nested_component node must have node_type=='nested_component'."""
        node = next(n for n in parent_comp.nodes.values() if n.node_type == "nested_component")
        assert node.node_type == "nested_component"

    def test_type11_subComponentUuid_populated(self, parent_comp):
        """The nested_component node's data must carry subComponentUuid."""
        node = next(n for n in parent_comp.nodes.values() if n.node_type == "nested_component")
        sub_uuid = node.data.get("subComponentUuid")
        assert sub_uuid, "subComponentUuid must be non-empty"
        # Must equal the child component's uuid
        assert sub_uuid == "41d97f14-743e-4043-8e33-f3e7267b039d"

    def test_type11_has_three_branches(self, parent_comp):
        """The nested_component node must produce exactly 3 branches (one per exit port)."""
        node = next(n for n in parent_comp.nodes.values() if n.node_type == "nested_component")
        assert len(node.branches) == 3

    def test_type11_branch_labels_match_exit_ports(self, parent_comp):
        """Branch labels must match the port names: Exit Node Yes/No/Unclassified."""
        node = next(n for n in parent_comp.nodes.values() if n.node_type == "nested_component")
        labels = {b.label for b in node.branches}
        assert "Exit Node Yes" in labels
        assert "Exit Node No" in labels
        assert "Exit Node Unclassified" in labels

    def test_type11_branch_targets_resolve_to_parent_nodes(self, parent_comp):
        """Each branch target_uuid must refer to a node in the parent component."""
        node = next(n for n in parent_comp.nodes.values() if n.node_type == "nested_component")
        parent_node_uuids = set(parent_comp.nodes.keys())
        for branch in node.branches:
            assert branch.target_uuid is not None, (
                f"Branch '{branch.label}' has no target_uuid"
            )
            assert branch.target_uuid in parent_node_uuids, (
                f"Branch '{branch.label}' target_uuid {branch.target_uuid!r} "
                f"not in parent component nodes"
            )

    def test_type11_branch_kind_is_exit(self, parent_comp):
        """All nested_component branches should have kind=='exit'."""
        node = next(n for n in parent_comp.nodes.values() if n.node_type == "nested_component")
        for branch in node.branches:
            assert branch.kind == "exit", (
                f"Branch '{branch.label}' kind should be 'exit', got {branch.kind!r}"
            )


# ---------------------------------------------------------------------------
# 2. Child component: type-4 exit_port nodes
# ---------------------------------------------------------------------------

class TestExitPortNodes:
    def test_child_parent_uuid(self, parent_comp, child_comp):
        """Child's parent_uuid must equal the parent component's uuid."""
        assert child_comp.parent_uuid == parent_comp.uuid

    def test_child_has_three_exit_port_nodes(self, child_comp):
        """Child must have exactly 3 exit_port nodes."""
        exit_ports = [n for n in child_comp.nodes.values() if n.node_type == "exit_port"]
        assert len(exit_ports) == 3, (
            f"Expected 3 exit_port nodes, found {len(exit_ports)}: "
            f"{[n.label for n in exit_ports]}"
        )

    def test_exit_port_not_goto_component(self, child_comp):
        """No type-4 node with empty appoint_node_id should be labeled goto_component."""
        bad = [
            n for n in child_comp.nodes.values()
            if n.node_type == "goto_component"
            and n.data.get("appoint_node_id", "") == ""
        ]
        assert bad == [], (
            f"These nodes should be exit_port, not goto_component: {[n.label for n in bad]}"
        )

    def test_exit_port_names_match(self, child_comp):
        """Exit port node labels must be Yes/No/Unclassified."""
        exit_ports = [n for n in child_comp.nodes.values() if n.node_type == "exit_port"]
        labels = {n.label for n in exit_ports}
        assert "Exit Node Yes" in labels
        assert "Exit Node No" in labels
        assert "Exit Node Unclassified" in labels

    def test_exit_port_branch_kind_is_exit(self, child_comp):
        """Each exit_port node must have exactly one branch with kind=='exit'."""
        exit_ports = [n for n in child_comp.nodes.values() if n.node_type == "exit_port"]
        for node in exit_ports:
            assert len(node.branches) == 1, (
                f"exit_port '{node.label}' should have 1 branch, got {len(node.branches)}"
            )
            assert node.branches[0].kind == "exit", (
                f"exit_port '{node.label}' branch kind should be 'exit', "
                f"got {node.branches[0].kind!r}"
            )

    def test_exit_port_branch_no_target(self, child_comp):
        """exit_port branches are terminal: no target_uuid or target_component."""
        exit_ports = [n for n in child_comp.nodes.values() if n.node_type == "exit_port"]
        for node in exit_ports:
            branch = node.branches[0]
            assert branch.target_uuid is None, (
                f"exit_port '{node.label}' should have no target_uuid"
            )
            assert branch.target_component is None, (
                f"exit_port '{node.label}' should have no target_component"
            )


# ---------------------------------------------------------------------------
# 3. goto_component disambiguation: populated appoint_node_id stays goto_component
# ---------------------------------------------------------------------------

class TestGotoComponentDisambiguation:
    """Ensure the exit_port disambiguation does NOT mis-classify real goto_component nodes."""

    def _make_goto_envelope(self):
        """Minimal type-4 envelope with populated appoint_node_id (a real goto)."""
        return {
            "type": 4,
            "name": "Go To Pitch",
            "is_default": True,
            "data": {
                "list": [],
                "appoint_node_id": "eb658c8c-dd71-41b2-b9f6-696280a460d4",
                "specificComponentName": "2. Pitch",
                "node_variables": [],
                "allow_jump_knowledges": [],
            },
        }

    def test_node_type_of_returns_goto_component_for_real_goto(self):
        """node_type_of on a type-4 envelope returns 'goto_component' (pre-disambiguation)."""
        envelope = self._make_goto_envelope()
        # node_type_of only reads the type integer — it should still return goto_component
        assert node_type_of(envelope) == "goto_component"

    def test_build_node_preserves_goto_component_when_appoint_node_id_populated(self):
        """_build_node must NOT reclassify a type-4 node with non-empty appoint_node_id."""
        envelope = self._make_goto_envelope()
        node = _build_node("goto-node-uuid", envelope, {})
        assert node.node_type == "goto_component"

    def test_real_goto_branch_has_target_component(self):
        """A real goto_component node must have target_component set."""
        envelope = self._make_goto_envelope()
        node = _build_node("goto-node-uuid", envelope, {})
        assert len(node.branches) == 1
        assert node.branches[0].target_component == "eb658c8c-dd71-41b2-b9f6-696280a460d4"
        assert node.branches[0].kind == "exit"

    def test_inline_build_components_goto_not_affected(self):
        """build_components on a component with real goto preserves goto_component."""
        comp_dict = {
            "componentUuid": "comp-goto-test",
            "name": "Goto Test",
            "sortIndex": 1,
            "details": {
                "goto1": {
                    "type": 4,
                    "name": "Go To Pitch",
                    "is_default": True,
                    "data": {
                        "list": [],
                        "appoint_node_id": "some-target-uuid",
                        "specificComponentName": "Target Component",
                        "node_variables": [],
                        "allow_jump_knowledges": [],
                    },
                },
            },
            "routes": {"goto1": {}},
        }
        components = build_components({"BizSpeechComponent": [comp_dict]})
        node = components[0].nodes["goto1"]
        assert node.node_type == "goto_component"
        assert node.branches[0].target_component == "some-target-uuid"


# ---------------------------------------------------------------------------
# 4. Top-level parent_uuid is "" or "0" (not a child)
# ---------------------------------------------------------------------------

class TestParentUuidField:
    def test_parent_comp_parent_uuid_is_zero_or_empty(self, parent_comp):
        """Top-level component's parent_uuid should be '' or '0' (not a real UUID)."""
        assert parent_comp.parent_uuid in ("", "0"), (
            f"Top-level comp parent_uuid={parent_comp.parent_uuid!r}, expected '' or '0'"
        )

    def test_child_comp_parent_uuid_is_parent_uuid(self, parent_comp, child_comp):
        """Child component's parent_uuid must match the parent component's uuid."""
        assert child_comp.parent_uuid == parent_comp.uuid
