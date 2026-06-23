"""Integration tests for build_flow_model against the real WIZ export.

Golden file: tests/golden/flowmodel_real.json (generated, then frozen).

Real export: speech2572824560161596380.unpacked.json (repo root).
Path derivation: this file lives at .claude/skills/wiz-checker/tests/test_flowmodel_build.py
  parents[4] == repo root  (tests/ -> wiz-checker/ -> skills/ -> .claude/ -> repo-root/)

Multi-round case (in this export): 6 KBs have multi_round populated; the other
24 have multi_round == None. The test documents which case it found.
"""
import json
import pytest
from pathlib import Path

from wizcheck.flowmodel import build_flow_model, flow_model_to_dict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# File now lives at .claude/skills/wiz-checker/tests/test_flowmodel_build.py
#   parents[0] = tests/
#   parents[1] = wiz-checker/
#   parents[2] = skills/
#   parents[3] = .claude/
#   parents[4] = repo-root/
_REPO_ROOT = Path(__file__).resolve().parents[4]
_REAL_EXPORT = _REPO_ROOT / "speech2572824560161596380.unpacked.json"
_GOLDEN = Path(__file__).resolve().parent / "golden" / "flowmodel_real.json"


def _skip_if_no_real():
    """Skip marker — applied to tests that need the real export."""
    return pytest.mark.skipif(
        not _REAL_EXPORT.exists(),
        reason=f"Real export not found: {_REAL_EXPORT}",
    )


@pytest.fixture(scope="module")
def real_data():
    if not _REAL_EXPORT.exists():
        pytest.skip(f"Real export not found: {_REAL_EXPORT}")
    return json.loads(_REAL_EXPORT.read_text("utf-8"))


@pytest.fixture(scope="module")
def built_dict(real_data):
    return flow_model_to_dict(build_flow_model(real_data))


@pytest.fixture(scope="module")
def golden_dict():
    if not _GOLDEN.exists():
        pytest.skip(f"Golden not found: {_GOLDEN}")
    return json.loads(_GOLDEN.read_text("utf-8"))


# ---------------------------------------------------------------------------
# Test 1 — exact golden match
# ---------------------------------------------------------------------------

class TestRealExportMatchesGolden:
    def test_real_export_matches_golden(self, built_dict, golden_dict):
        """flow_model_to_dict(build_flow_model(real)) must equal the frozen golden."""
        assert built_dict == golden_dict


# ---------------------------------------------------------------------------
# Test 2 — real component names and known node types
# ---------------------------------------------------------------------------

class TestComponentsHaveRealNamesAndKnownTypes:
    def test_at_least_one_component(self, built_dict):
        assert len(built_dict["components"]) >= 1

    def test_component_names_are_real(self, built_dict):
        """Components should have human-readable names, not empty strings."""
        names = [c["name"] for c in built_dict["components"]]
        non_empty = [n for n in names if n.strip()]
        assert len(non_empty) >= 1, f"All component names are blank: {names}"

    def test_unknown_node_fraction_under_20_percent(self, built_dict):
        """Across all nodes, 'unknown' must be < 20 % of total."""
        all_types = [
            n["node_type"]
            for c in built_dict["components"]
            for n in c["nodes"].values()
        ]
        total = len(all_types)
        assert total > 0, "No nodes found in any component"
        unknown_count = sum(1 for t in all_types if t == "unknown")
        fraction = unknown_count / total
        assert fraction < 0.2, (
            f"Too many unknown node types: {unknown_count}/{total} = {fraction:.1%}"
        )

    def test_expected_component_count(self, built_dict):
        """Real export has 16 components — regression guard."""
        assert len(built_dict["components"]) == 16

    def test_expected_kb_count(self, built_dict):
        """Real export has 30 KBs — regression guard."""
        assert len(built_dict["knowledge_bases"]) == 30


# ---------------------------------------------------------------------------
# Test 3 — at least one cross-component edge
# ---------------------------------------------------------------------------

class TestAtLeastOneCrossComponentEdge:
    def test_at_least_one_cross_component_edge(self, built_dict):
        """At least one node must have a branch with a non-null target_component."""
        cross_edges = [
            (c["name"], n["uuid"], b["target_component"])
            for c in built_dict["components"]
            for n in c["nodes"].values()
            for b in n["branches"]
            if b.get("target_component") is not None
        ]
        assert len(cross_edges) >= 1, "No cross-component edges found"

    def test_cross_component_edge_has_valid_label(self, built_dict):
        """A cross-component edge should carry the human-readable component name."""
        cross_edges = [
            b
            for c in built_dict["components"]
            for n in c["nodes"].values()
            for b in n["branches"]
            if b.get("target_component") is not None
        ]
        assert any(b["label"] for b in cross_edges), (
            "All cross-component edges have blank labels"
        )


# ---------------------------------------------------------------------------
# Test 4 — at least one talk intent branch with a label
# ---------------------------------------------------------------------------

class TestAtLeastOneTalkIntentBranch:
    def test_at_least_one_intent_branch_with_label(self, built_dict):
        """At least one branch must have kind='intent' and a non-empty label."""
        intent_branches = [
            b
            for c in built_dict["components"]
            for n in c["nodes"].values()
            for b in n["branches"]
            if b.get("kind") == "intent" and b.get("label")
        ]
        assert len(intent_branches) >= 1, "No labelled intent branches found"


# ---------------------------------------------------------------------------
# Test 5 — multi-round
# ---------------------------------------------------------------------------

class TestMultiRound:
    """In the real export, 6 KBs have multi_round populated; 24 have None.

    If the export changes, the test self-documents which case it observed.
    """

    def test_multi_round_case_documented(self, built_dict):
        kbs = built_dict["knowledge_bases"]
        with_mr = [kb for kb in kbs if kb.get("multi_round") is not None]
        without_mr = [kb for kb in kbs if kb.get("multi_round") is None]

        # In this export, 6 KBs have multi_round.
        if with_mr:
            # Case A — multi_round present: each must have non-empty components
            for kb in with_mr:
                mr = kb["multi_round"]
                assert isinstance(mr, dict), (
                    f"KB {kb['knowledge_id']} multi_round is not a dict: {type(mr)}"
                )
                assert len(mr["components"]) >= 1, (
                    f"KB {kb['knowledge_id']} multi_round has no components"
                )
                assert mr["knowledge_bases"] == [], (
                    f"KB {kb['knowledge_id']} multi_round.knowledge_bases should be []"
                )
            # document for the reader
            print(
                f"\n[multi_round] Case A: {len(with_mr)} KBs have multi_round; "
                f"{len(without_mr)} have None."
            )
        else:
            # Case B — no multi_round in this export at all
            for kb in kbs:
                assert kb.get("multi_round") is None, (
                    f"KB {kb['knowledge_id']} unexpectedly has multi_round"
                )
            print(
                f"\n[multi_round] Case B: all {len(kbs)} KBs have multi_round=None."
            )

    def test_multi_round_component_has_known_node_types(self, built_dict):
        """Nodes inside a multi_round FlowModel must also be mostly known types."""
        kbs_with_mr = [
            kb for kb in built_dict["knowledge_bases"]
            if kb.get("multi_round") is not None
        ]
        if not kbs_with_mr:
            pytest.skip("No KBs with multi_round in this export")

        all_types = [
            n["node_type"]
            for kb in kbs_with_mr
            for c in kb["multi_round"]["components"]
            for n in c["nodes"].values()
        ]
        assert len(all_types) > 0
        unknown_fraction = sum(1 for t in all_types if t == "unknown") / len(all_types)
        assert unknown_fraction < 0.2, (
            f"Too many unknown types inside multi_round: {unknown_fraction:.1%}"
        )
