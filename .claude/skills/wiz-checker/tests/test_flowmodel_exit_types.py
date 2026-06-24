"""Tests for exit-family node type reading — Task 4 (TDD red → green).

Ground-truth fixtures (from wiz-builder):
  ref_exit_multicomp_25.json — comp[0]: goto (type 4); comp[1]: hangup (type 2, is_transfer=0)
  ref_exit_multicomp_26.json — comp[0]: goto (type 4); comp[1]: transfer (type 13, is_transfer=1)

These tests deliberately exercise the exact bug:
  - type 13 was missing from NODE_TYPE_MAP → read as "unknown"
  - type 2 with is_transfer=1 was treated as transfer → wrong (type 2 is always hangup)
"""
import json
from pathlib import Path

import pytest
from wizcheck.flowmodel import build_components

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------
# test file: .claude/skills/wiz-checker/tests/test_flowmodel_exit_types.py
#   parents[0] = tests/
#   parents[1] = wiz-checker/
#   parents[2] = skills/
#   parents[3] = .claude/
#   parents[4] = repo-root/
_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURE_DIR = _REPO_ROOT / ".claude" / "skills" / "wiz-builder" / "tests" / "fixtures"
_REF_25 = _FIXTURE_DIR / "ref_exit_multicomp_25.json"
_REF_26 = _FIXTURE_DIR / "ref_exit_multicomp_26.json"

# Known UUIDs from fixture inspection
_COMP0_UUID = "8161e722-1731-4112-a6de-1628f573a88b"
_COMP1_UUID = "37d91736-c70f-453b-a9f4-bbfe4a48f1a8"
_GOTO_NODE_UUID = "ede542b7-6763-4c32-b375-cb0be7ddf7b6"   # type 4 in comp[0]
# type 2 in ref_25; type 13 in ref_26 — same UUID, different fixture
_EXIT_NODE_UUID = "b0dee28c-165e-4e52-b316-f4de5b313236"


@pytest.fixture(scope="module")
def comps_25():
    if not _REF_25.exists():
        pytest.skip(f"Fixture not found: {_REF_25}")
    data = json.loads(_REF_25.read_text("utf-8"))
    return build_components(data)


@pytest.fixture(scope="module")
def comps_26():
    if not _REF_26.exists():
        pytest.skip(f"Fixture not found: {_REF_26}")
    data = json.loads(_REF_26.read_text("utf-8"))
    return build_components(data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_comp(comps, uuid: str):
    return next((c for c in comps if c.uuid == uuid), None)


# ---------------------------------------------------------------------------
# ref_25: comp[1] has type-2 hangup node
# ---------------------------------------------------------------------------

class TestRef25HangupNode:
    def test_comp1_exit_node_type_is_exit(self, comps_25):
        comp1 = _find_comp(comps_25, _COMP1_UUID)
        assert comp1 is not None, "comp[1] not found"
        node = comp1.nodes.get(_EXIT_NODE_UUID)
        assert node is not None, f"Exit node {_EXIT_NODE_UUID} not found in comp[1]"
        assert node.node_type == "exit"

    def test_comp1_exit_node_branch_terminal_is_hangup(self, comps_25):
        comp1 = _find_comp(comps_25, _COMP1_UUID)
        node = comp1.nodes[_EXIT_NODE_UUID]
        assert len(node.branches) == 1
        assert node.branches[0].terminal == "hangup"

    def test_comp1_exit_node_branch_kind_is_exit(self, comps_25):
        comp1 = _find_comp(comps_25, _COMP1_UUID)
        node = comp1.nodes[_EXIT_NODE_UUID]
        assert node.branches[0].kind == "exit"


# ---------------------------------------------------------------------------
# ref_26: comp[1] has type-13 transfer node
# ---------------------------------------------------------------------------

class TestRef26TransferNode:
    def test_comp1_transfer_node_type_is_transfer(self, comps_26):
        """type 13 must map to 'transfer', not 'unknown'."""
        comp1 = _find_comp(comps_26, _COMP1_UUID)
        assert comp1 is not None, "comp[1] not found"
        node = comp1.nodes.get(_EXIT_NODE_UUID)
        assert node is not None, f"Transfer node {_EXIT_NODE_UUID} not found in comp[1]"
        assert node.node_type == "transfer", (
            f"Expected 'transfer', got '{node.node_type}' — type 13 missing from NODE_TYPE_MAP?"
        )

    def test_comp1_transfer_node_branch_terminal_is_transfer(self, comps_26):
        """type-13 branch terminal must be 'transfer'."""
        comp1 = _find_comp(comps_26, _COMP1_UUID)
        node = comp1.nodes[_EXIT_NODE_UUID]
        assert len(node.branches) == 1
        assert node.branches[0].terminal == "transfer", (
            f"Expected terminal='transfer', got '{node.branches[0].terminal}'"
        )

    def test_comp1_transfer_node_branch_kind_is_exit(self, comps_26):
        comp1 = _find_comp(comps_26, _COMP1_UUID)
        node = comp1.nodes[_EXIT_NODE_UUID]
        assert node.branches[0].kind == "exit"


# ---------------------------------------------------------------------------
# ref_25: comp[0] has type-4 goto node pointing at comp[1]
# ---------------------------------------------------------------------------

class TestRef25GotoNode:
    def test_comp0_goto_node_type_is_goto_component(self, comps_25):
        comp0 = _find_comp(comps_25, _COMP0_UUID)
        assert comp0 is not None, "comp[0] not found"
        node = comp0.nodes.get(_GOTO_NODE_UUID)
        assert node is not None, f"Goto node {_GOTO_NODE_UUID} not found in comp[0]"
        assert node.node_type == "goto_component"

    def test_comp0_goto_node_target_component_is_comp1(self, comps_25):
        """Goto node's target_component must equal comp[1]'s componentUuid."""
        comp0 = _find_comp(comps_25, _COMP0_UUID)
        node = comp0.nodes[_GOTO_NODE_UUID]
        assert len(node.branches) == 1
        assert node.branches[0].target_component == _COMP1_UUID, (
            f"Expected target_component='{_COMP1_UUID}', "
            f"got '{node.branches[0].target_component}'"
        )

    def test_comp0_goto_node_branch_kind_is_exit(self, comps_25):
        comp0 = _find_comp(comps_25, _COMP0_UUID)
        node = comp0.nodes[_GOTO_NODE_UUID]
        assert node.branches[0].kind == "exit"


# ---------------------------------------------------------------------------
# Synthetic: type-2 node with is_transfer=1 must NOT yield "transfer"
# (type-2 is always hangup; transfer is type-13 only)
# ---------------------------------------------------------------------------

class TestType2AlwaysHangup:
    """Regression: before fix, type-2 + is_transfer=1 yielded terminal='transfer'.
    After fix, type-2 is always 'hangup' regardless of is_transfer flag.
    """

    def _make_comp_type2_is_transfer_1(self):
        return {
            "BizSpeechComponent": [
                {
                    "componentUuid": "comp-type2-istransfer",
                    "name": "Type2 Transfer Flag",
                    "sortIndex": 1,
                    "details": {
                        "exit-node": {
                            "type": 2,
                            "name": "Exit Node",
                            "is_default": True,
                            "data": {
                                "list": [],
                                "is_transfer": 1,
                                "node_variables": [],
                                "allow_jump_knowledges": [],
                            },
                        },
                    },
                    "routes": {"exit-node": {}},
                }
            ]
        }

    def test_type2_with_is_transfer_1_yields_hangup_not_transfer(self):
        """type-2 node is always hangup — is_transfer flag does not override this."""
        comps = build_components(self._make_comp_type2_is_transfer_1())
        node = comps[0].nodes["exit-node"]
        assert node.node_type == "exit"
        assert len(node.branches) == 1
        assert node.branches[0].terminal == "hangup", (
            f"type-2 with is_transfer=1 should still be 'hangup', "
            f"got '{node.branches[0].terminal}'"
        )
