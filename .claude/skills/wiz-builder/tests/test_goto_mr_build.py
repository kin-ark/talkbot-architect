"""Test builder serializer for goto_mr (type 9) nodes."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from wizbuilder.compile import compile_manifest
from wizbuilder.manifest import ManifestError
from wizcheck.checks import run_all_checks
from wizcheck.flowmodel import unwrap
from wizcheck.parser import parse_dict


VALID_MANIFEST = """
name: GotoMR Demo
branch: dev
language: IDN
knowledge_bases:
  - name: "K1"
    intents: ["Intent1"]
    answers: ["hai"]
    multi_round: "MR A"
  - name: "K2"
    intents: ["Intent2"]
    answers: ["yok"]
    multi_round: "MR B"
custom_intents:
  - name: "Intent1"
    language: IDN
    keywords: ["x"]
    user_responses: ["y"]
  - name: "Intent2"
    language: IDN
    keywords: ["z"]
    user_responses: ["w"]
canvases:
  - name: "Main"
    nodes:
      - {id: greet, type: talk, prompt: "halo"}
      - {id: greet_exit, type: exit, prompt: "bye"}
    edges: [{from: greet, branch: Unclassified, to: greet_exit}]
  - name: "MR A"
    nodes:
      - {id: mr1, type: talk, prompt: "putaran A"}
      - {id: jump, type: goto_mr, config: {target: "MR B"}}
    edges: [{from: mr1, branch: Unclassified, to: jump}]
  - name: "MR B"
    nodes:
      - {id: mr2, type: talk, prompt: "putaran B"}
      - {id: mr3, type: exit, prompt: "selesai"}
    edges: [{from: mr2, branch: Unclassified, to: mr3}]
"""


def test_goto_mr_builds_type9_clean():
    """goto_mr inside MR A targeting MR B compiles to type 9 node with multiple_appoint_id, empty routes, no SCS."""
    # Create and compile the manifest
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_path.write_text(VALID_MANIFEST, encoding="utf-8")
        out_path = Path(tmpdir) / "speech.json"
        compile_manifest(manifest_path, out_path)

        data = json.loads(out_path.read_text(encoding="utf-8"))

    # Check no errors
    all_findings = run_all_checks(parse_dict(data))
    errs = [f for f in all_findings if f.severity.name == "ERROR"]
    assert errs == [], f"Build produced errors: {errs}"

    # WIZ107 regression: a component whose only terminal is a goto_mr must NOT be
    # flagged "no terminal" (goto_mr is terminal). MR A ends in goto_mr.
    assert not [f for f in all_findings if f.code == "WIZ107"], \
        "goto_mr must satisfy the component-has-terminal check (WIZ107)"

    # Find the type-9 node in the MR A component
    comps = unwrap(data["BizSpeechComponent"])
    mr_a_comp = None
    mr_b_uuid = None
    for c in comps:
        if c.get("name") == "MR A":
            mr_a_comp = c
        elif c.get("name") == "MR B":
            mr_b_uuid = c.get("componentUuid")

    assert mr_a_comp, "expected MR A component in the build"
    assert mr_b_uuid, "expected MR B component in the build"

    # Find the type-9 node within MR A
    det = mr_a_comp.get("details")
    tree = json.loads(det) if isinstance(det, str) else det
    found = None
    for n in (tree or {}).values():
        if (n.get("data") or {}).get("type") == 9:
            found = n

    assert found, "expected a type-9 node in MR A component"
    d = found["data"]

    # Verify type 9
    assert d["type"] == 9, f"Expected type 9, got {d['type']}"

    # Verify multiple_appoint_id is set (points to MR B component)
    assert d["multiple_appoint_id"] == mr_b_uuid, \
        f"multiple_appoint_id must point to MR B ({mr_b_uuid}), got {d['multiple_appoint_id']!r}"

    # Verify appoint_node_id is empty
    assert d["appoint_node_id"] == "", f"appoint_node_id must be empty, got {d['appoint_node_id']!r}"

    # Verify empty routes
    routes = mr_a_comp.get("routes")
    routes = json.loads(routes) if isinstance(routes, str) else routes
    node_routes = routes.get(d["id"], {})
    assert node_routes == {}, f"goto_mr is terminal: routes must be empty, got {node_routes}"

    # Verify no SentenceCutSpeech row for this node
    scs = json.loads(data["SentenceCutSpeech"])
    node_scs = [row for row in scs if row.get("id") == d["id"]]
    assert node_scs == [], f"goto_mr must not emit SentenceCutSpeech row, found {len(node_scs)}"

    # Verify no topFloorDetails row for this node
    comp_top_floor = json.loads(mr_a_comp.get("topFloorDetails", "[]"))
    node_top_floor = [row for row in comp_top_floor if row.get("id") == d["id"]]
    assert node_top_floor == [], f"goto_mr must not emit topFloorDetails row, found {len(node_top_floor)}"

    # Verify MR A is category 2 (multi-round)
    assert mr_a_comp.get("category") == 2, f"MR A should be category 2, got {mr_a_comp.get('category')}"


INVALID_MANIFEST_GOTO_MR_IN_NORMAL = """
name: GotoMR In Normal Canvas
branch: dev
language: IDN
custom_intents:
  - {name: Intent1, language: IDN, keywords: ["x"], user_responses: ["x"]}
  - {name: Intent2, language: IDN, keywords: ["y"], user_responses: ["y"]}
knowledge_bases:
  - {name: "K1", intents: ["Intent1"], answers: ["hai"], multi_round: "MR A"}
  - {name: "K2", intents: ["Intent2"], answers: ["yok"], multi_round: "MR B"}
canvases:
  - name: "Main"
    nodes:
      - {id: jump, type: goto_mr, config: {target: "MR A"}}
    edges: []
  - name: "MR A"
    nodes:
      - {id: a1, type: talk, prompt: "hi"}
      - {id: a2, type: exit, prompt: "bye"}
    edges: [{from: a1, branch: Unclassified, to: a2}]
  - name: "MR B"
    nodes:
      - {id: b1, type: talk, prompt: "hi2"}
      - {id: b2, type: exit, prompt: "bye2"}
    edges: [{from: b1, branch: Unclassified, to: b2}]
"""

INVALID_MANIFEST_NON_MR_TARGET = """
name: GotoMR NonMR Target
branch: dev
language: IDN
custom_intents:
  - {name: Intent1, language: IDN, keywords: ["x"], user_responses: ["x"]}
knowledge_bases:
  - {name: "K1", intents: ["Intent1"], answers: ["hai"], multi_round: "MR A"}
canvases:
  - name: "Main"
    nodes:
      - {id: m, type: talk, prompt: "hi"}
      - {id: m_exit, type: exit, prompt: "bye"}
    edges: [{from: m, branch: Unclassified, to: m_exit}]
  - name: "MR A"
    nodes:
      - {id: a1, type: talk, prompt: "hi2"}
      - {id: jump, type: goto_mr, config: {target: "Normal"}}
    edges: [{from: a1, branch: Unclassified, to: jump}]
  - name: "Normal"
    nodes:
      - {id: n1, type: talk, prompt: "normal"}
      - {id: n2, type: exit, prompt: "bye"}
    edges: [{from: n1, branch: Unclassified, to: n2}]
"""


def test_goto_mr_in_normal_canvas_rejected():
    """goto_mr in a non-multi-round canvas raises ManifestError at load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_path.write_text(INVALID_MANIFEST_GOTO_MR_IN_NORMAL, encoding="utf-8")
        out_path = Path(tmpdir) / "speech.json"

        # Should raise ManifestError because goto_mr is in "Main" which is not a multi_round target
        with pytest.raises((ManifestError, ValueError), match="only valid inside a multi-round"):
            compile_manifest(manifest_path, out_path)


def test_goto_mr_target_must_be_multi_round():
    """goto_mr targeting a non-multi-round canvas raises ManifestError at build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_path.write_text(INVALID_MANIFEST_NON_MR_TARGET, encoding="utf-8")
        out_path = Path(tmpdir) / "speech.json"

        # Should raise ManifestError because "Normal" is not a multi_round target
        with pytest.raises((ManifestError, ValueError)):
            compile_manifest(manifest_path, out_path)
