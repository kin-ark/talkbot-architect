"""Regression test: goto_kb (type 8) terminal-node read — M2-T3.

Locks the checker's read path for type-8 nodes:
  - flow_constants: 8 → "goto_kb"
  - flowmodel: _build_branches("goto_kb") emits BranchEdge(kind="exit", target_kb=<int>)
  - parse_dict + run_all_checks: clean builder output stays clean; absent KB id tolerated.

Cross-skill import: wiz-builder scripts are prepended to sys.path (same pattern as
test_kb_authoring.py and test_flowmodel_exit_types.py).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — must precede any wizbuilder import
# ---------------------------------------------------------------------------
# This file lives at:
#   .claude/skills/wiz-checker/tests/test_goto_kb.py
#   parents[0] = tests/
#   parents[1] = wiz-checker/
#   parents[2] = skills/
#   parents[3] = .claude/
#   parents[4] = repo/worktree root
_SKILLS_DIR = Path(__file__).resolve().parents[2]       # .claude/skills/
_BUILDER_SCRIPTS = _SKILLS_DIR / "wiz-builder" / "scripts"
_BUILDER_FIXTURES = _SKILLS_DIR / "wiz-builder" / "tests" / "fixtures"

if str(_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_BUILDER_SCRIPTS))

from wizcheck.checks import run_all_checks  # noqa: E402
from wizcheck.flow_constants import NODE_TYPE_MAP  # noqa: E402
from wizcheck.flowmodel import build_flow_model  # noqa: E402
from wizcheck.parser import parse_dict  # noqa: E402
from wizcheck.report import Severity  # noqa: E402

try:
    from wizbuilder.compile import compile_manifest  # noqa: E402
    _HAS_BUILDER = True
except ImportError:
    _HAS_BUILDER = False

_MANIFEST_GOTO_KB = _BUILDER_FIXTURES / "manifest_goto_kb.yaml"

_SKIP_NO_BUILDER = pytest.mark.skipif(
    not _HAS_BUILDER, reason="wiz-builder not on sys.path"
)
_SKIP_NO_FIXTURE = pytest.mark.skipif(
    not _MANIFEST_GOTO_KB.exists(),
    reason=f"manifest_goto_kb.yaml not found at {_MANIFEST_GOTO_KB}",
)


# ===========================================================================
# 0. Constants — no builder needed
# ===========================================================================

class TestFlowConstants:
    """flow_constants.NODE_TYPE_MAP must map 8 → 'goto_kb'."""

    def test_type_8_maps_to_goto_kb(self):
        assert 8 in NODE_TYPE_MAP, "NODE_TYPE_MAP must contain key 8"
        assert NODE_TYPE_MAP[8] == "goto_kb", (
            f"NODE_TYPE_MAP[8] must be 'goto_kb', got {NODE_TYPE_MAP[8]!r}"
        )


# ===========================================================================
# 1. FlowModel read — unit test (no builder needed)
# ===========================================================================

_SYNTHETIC_NODE_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
_SYNTHETIC_COMP_UUID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"


def _make_export_with_goto_kb_node(kb_id: int | str) -> dict:
    """Return a minimal raw export dict containing one goto_kb node.

    Uses real UUID strings so parse_dict doesn't reject them.
    build_flow_model tests use this too; they only need a valid dict, not a
    parse_dict-compatible one.
    """
    return {
        "BizSpeechComponent": [
            {
                "componentUuid": _SYNTHETIC_COMP_UUID,
                "name": "Main",
                "sortIndex": 1,
                "parentUuid": "0",
                "details": {
                    _SYNTHETIC_NODE_UUID: {
                        "type": 8,
                        "name": "Go To KB",
                        "is_default": True,
                        "data": {
                            "type": 8,
                            "appoint_knowledge_id": kb_id,
                            "list": [],
                            "node_variables": [],
                            "allow_jump_knowledges": [],
                        },
                    }
                },
                "routes": {_SYNTHETIC_NODE_UUID: {}},
            }
        ],
        "BizKnowledgeInfo": [],
        "SpeechIntent": [],
        "SpeechVariable": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
        "BizSpeechCanvas": [],
        "BizSpeechRoute": [],
    }


class TestGotoKbFlowModelRead:
    """build_flow_model must read type-8 as goto_kb with one exit branch."""

    def test_node_type_is_goto_kb(self):
        data = _make_export_with_goto_kb_node(kb_id=12345)
        fm = build_flow_model(data)
        assert len(fm.components) == 1
        node = fm.components[0].nodes[_SYNTHETIC_NODE_UUID]
        assert node.node_type == "goto_kb", (
            f"Expected node_type='goto_kb', got {node.node_type!r}"
        )

    def test_branch_kind_is_exit(self):
        data = _make_export_with_goto_kb_node(kb_id=12345)
        fm = build_flow_model(data)
        node = fm.components[0].nodes[_SYNTHETIC_NODE_UUID]
        assert len(node.branches) == 1, (
            f"Expected exactly 1 branch for goto_kb, got {len(node.branches)}"
        )
        assert node.branches[0].kind == "exit"

    def test_branch_target_kb_is_int(self):
        data = _make_export_with_goto_kb_node(kb_id=12345)
        fm = build_flow_model(data)
        node = fm.components[0].nodes[_SYNTHETIC_NODE_UUID]
        assert node.branches[0].target_kb == 12345, (
            f"Expected target_kb=12345, got {node.branches[0].target_kb!r}"
        )

    def test_branch_label_is_go_to_kb(self):
        data = _make_export_with_goto_kb_node(kb_id=12345)
        fm = build_flow_model(data)
        node = fm.components[0].nodes[_SYNTHETIC_NODE_UUID]
        assert node.branches[0].label == "go to KB"

    def test_branch_terminal_is_none(self):
        """goto_kb is an exit-to-KB, not hangup or transfer — terminal must be None."""
        data = _make_export_with_goto_kb_node(kb_id=12345)
        fm = build_flow_model(data)
        node = fm.components[0].nodes[_SYNTHETIC_NODE_UUID]
        assert node.branches[0].terminal is None

    def test_string_kb_id_coerced_to_int(self):
        """appoint_knowledge_id may arrive as a string; must coerce to int."""
        data = _make_export_with_goto_kb_node(kb_id="67890")
        fm = build_flow_model(data)
        node = fm.components[0].nodes[_SYNTHETIC_NODE_UUID]
        assert node.branches[0].target_kb == 67890


# ===========================================================================
# 2. Builder-driven regression — parse_dict + run_all_checks
# ===========================================================================

@_SKIP_NO_BUILDER
@_SKIP_NO_FIXTURE
def test_goto_kb_builder_export_parse_no_crash(tmp_path):
    """compile_manifest on manifest_goto_kb.yaml must not crash parse_dict."""
    out = tmp_path / "speech_goto_kb.json"
    compile_manifest(_MANIFEST_GOTO_KB, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    wf = parse_dict(data)   # must not raise
    assert wf is not None


@_SKIP_NO_BUILDER
@_SKIP_NO_FIXTURE
def test_goto_kb_builder_export_run_all_checks_clean(tmp_path):
    """A builder-clean goto_kb export must produce no ERROR-severity findings."""
    out = tmp_path / "speech_goto_kb_clean.json"
    compile_manifest(_MANIFEST_GOTO_KB, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    wf = parse_dict(data)
    findings = run_all_checks(wf)
    errors = [f for f in findings if f.severity is Severity.ERROR]
    assert not errors, (
        "Clean goto_kb export must produce no ERROR findings; got:\n"
        + "\n".join(f"  [{f.code}] {f.message}" for f in errors)
    )


@_SKIP_NO_BUILDER
@_SKIP_NO_FIXTURE
def test_goto_kb_node_appears_in_flow_model(tmp_path):
    """build_flow_model on a built goto_kb export must contain a goto_kb node."""
    out = tmp_path / "speech_goto_kb_fm.json"
    compile_manifest(_MANIFEST_GOTO_KB, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    fm = build_flow_model(data)

    goto_kb_nodes = [
        node
        for comp in fm.components
        for node in comp.nodes.values()
        if node.node_type == "goto_kb"
    ]
    assert len(goto_kb_nodes) >= 1, (
        "Expected at least one goto_kb node in FlowModel from built export; "
        f"node types found: {[n.node_type for c in fm.components for n in c.nodes.values()]}"
    )
    gkb = goto_kb_nodes[0]
    assert len(gkb.branches) == 1
    assert gkb.branches[0].kind == "exit"
    assert gkb.branches[0].target_kb is not None, (
        "goto_kb branch must carry a numeric target_kb (appoint_knowledge_id)"
    )


# ===========================================================================
# 3. Absent KB id is TOLERATED — no hard ERROR (orphan/library-ref style)
# ===========================================================================

def test_absent_kb_id_tolerated_by_flowmodel():
    """A goto_kb node pointing at a non-existent KB id must not crash flowmodel.

    The checker has no cross-reference check between goto_kb.appoint_knowledge_id
    and BizKnowledgeInfo; absent ids are treated like orphan/library refs.
    """
    data = _make_export_with_goto_kb_node(kb_id=999999999)
    fm = build_flow_model(data)   # must not raise
    node = fm.components[0].nodes[_SYNTHETIC_NODE_UUID]
    assert node.node_type == "goto_kb"
    assert node.branches[0].target_kb == 999999999


def test_absent_kb_id_tolerated_by_run_all_checks():
    """parse_dict + run_all_checks on a goto_kb node with absent KB id must
    produce no ERROR finding attributed specifically to the goto_kb.

    The checker does not cross-check appoint_knowledge_id against
    BizKnowledgeInfo; absent ids are silently tolerated (library/orphan pattern).
    """
    data = _make_export_with_goto_kb_node(kb_id=999999999)
    # Add a minimal Unclassified intent so WIZ301 doesn't fire and muddy the picture
    data["SpeechIntent"] = [
        {"intentId": 1, "intentName": "Unclassified", "language": "IDN"}
    ]
    wf = parse_dict(data)
    findings = run_all_checks(wf)
    errors = [f for f in findings if f.severity is Severity.ERROR]
    # There must be no ERROR specifically naming/implicating the goto_kb node's
    # absent KB reference.  We allow errors from OTHER causes (none expected for
    # this minimal export, but be robust).  Key invariant: no crash + no ERROR
    # with "goto_kb" or "appoint_knowledge_id" in its message.
    goto_kb_errors = [
        f for f in errors
        if "goto_kb" in f.message.lower() or "appoint_knowledge_id" in f.message.lower()
    ]
    assert not goto_kb_errors, (
        "Absent KB id in goto_kb node must NOT produce an ERROR; "
        "got:\n" + "\n".join(f"  [{f.code}] {f.message}" for f in goto_kb_errors)
    )


@_SKIP_NO_BUILDER
@_SKIP_NO_FIXTURE
def test_absent_kb_id_tolerated_in_built_export(tmp_path):
    """Build a real goto_kb export, swap the KB id to a bogus value, and assert
    run_all_checks raises no exception and emits no goto_kb-attributed ERROR.

    Built exports use double JSON-encoding:
      - BizSpeechComponent is a JSON-encoded string (list)
      - Each component's 'details' is also a JSON-encoded string (dict)
    The patch must decode both layers, mutate, and re-encode.
    """
    out = tmp_path / "speech_goto_kb_absent.json"
    compile_manifest(_MANIFEST_GOTO_KB, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    data = copy.deepcopy(data)

    # Decode the outer BizSpeechComponent JSON string (or list — handle both)
    bsc_raw = data.get("BizSpeechComponent", [])
    comps: list = json.loads(bsc_raw) if isinstance(bsc_raw, str) else bsc_raw

    patched = 0
    for comp in comps:
        if not isinstance(comp, dict):
            continue
        details_raw = comp.get("details")
        if details_raw is None:
            continue
        details: dict = json.loads(details_raw) if isinstance(details_raw, str) else details_raw
        for _node_uuid, envelope in details.items():
            if not isinstance(envelope, dict):
                continue
            if envelope.get("type") != 8:
                continue
            node_data = envelope.get("data", {})
            if isinstance(node_data, dict):
                node_data["appoint_knowledge_id"] = "999999999"
                patched += 1
        # Write details back as JSON string if it came in as one
        comp["details"] = json.dumps(details) if isinstance(details_raw, str) else details

    assert patched >= 1, "Expected to patch at least one goto_kb node (type 8)"

    # Write BizSpeechComponent back in the same form it came in
    data["BizSpeechComponent"] = json.dumps(comps) if isinstance(bsc_raw, str) else comps

    wf = parse_dict(data)           # must not raise
    findings = run_all_checks(wf)   # must not raise

    goto_kb_errors = [
        f for f in findings
        if f.severity is Severity.ERROR
        and ("goto_kb" in f.message.lower() or "appoint_knowledge_id" in f.message.lower())
    ]
    assert not goto_kb_errors, (
        "Absent KB id in goto_kb node (patched built export) must NOT produce an ERROR; "
        "got:\n" + "\n".join(f"  [{f.code}] {f.message}" for f in goto_kb_errors)
    )
