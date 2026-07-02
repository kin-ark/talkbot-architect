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
    intents: ["SomeIntent"]
    answers: ["hai"]
    multi_round: "MR Flow"
custom_intents:
  - name: "SomeIntent"
    language: IDN
    keywords: ["x"]
    user_responses: ["y"]
canvases:
  - name: "Main"
    nodes:
      - {id: greet, type: talk, prompt: "halo"}
      - {id: jump, type: goto_mr, config: {target: "MR Flow"}}
    edges: [{from: greet, branch: Unclassified, to: jump}]
  - name: "MR Flow"
    nodes:
      - {id: mr1, type: talk, prompt: "putaran"}
      - {id: mr2, type: exit, prompt: "selesai"}
    edges: [{from: mr1, branch: Unclassified, to: mr2}]
"""


def test_goto_mr_builds_type9_clean():
    """goto_mr compiles to type 9 node with multiple_appoint_id, empty routes, no SCS."""
    # Create and compile the manifest
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_path.write_text(VALID_MANIFEST, encoding="utf-8")
        out_path = Path(tmpdir) / "speech.json"
        compile_manifest(manifest_path, out_path)

        data = json.loads(out_path.read_text(encoding="utf-8"))

    # Check no errors
    errs = [f for f in run_all_checks(parse_dict(data)) if f.severity.name == "ERROR"]
    assert errs == [], f"Build produced errors: {errs}"

    # Find the type-9 node
    comps = unwrap(data["BizSpeechComponent"])
    found = None
    for c in comps:
        det = c.get("details")
        tree = json.loads(det) if isinstance(det, str) else det
        for n in (tree or {}).values():
            if (n.get("data") or {}).get("type") == 9:
                found = (c, n)
    assert found, "expected a type-9 node in the build"
    comp, node = found

    d = node["data"]

    # Verify type 9
    assert d["type"] == 9, f"Expected type 9, got {d['type']}"

    # Verify multiple_appoint_id is set (non-empty UUID, points to MR Flow component)
    assert d["multiple_appoint_id"], "multiple_appoint_id must be the resolved target uuid"

    # Verify appoint_node_id is empty
    assert d["appoint_node_id"] == "", f"appoint_node_id must be empty, got {d['appoint_node_id']!r}"

    # Verify empty routes
    routes = comp.get("routes")
    routes = json.loads(routes) if isinstance(routes, str) else routes
    node_routes = routes.get(d["id"], {})
    assert node_routes == {}, f"goto_mr is terminal: routes must be empty, got {node_routes}"

    # Verify no SentenceCutSpeech row for this node
    scs = json.loads(data["SentenceCutSpeech"])
    node_scs = [row for row in scs if row.get("id") == d["id"]]
    assert node_scs == [], f"goto_mr must not emit SentenceCutSpeech row, found {len(node_scs)}"

    # Verify no topFloorDetails row for this node
    comp_top_floor = json.loads(comp.get("topFloorDetails", "[]"))
    node_top_floor = [row for row in comp_top_floor if row.get("id") == d["id"]]
    assert node_top_floor == [], f"goto_mr must not emit topFloorDetails row, found {len(node_top_floor)}"


INVALID_MANIFEST_NON_MR_TARGET = """
name: GotoMR NonMR Target
branch: dev
language: IDN
canvases:
  - name: "Main"
    nodes:
      - {id: greet, type: talk, prompt: "halo"}
      - {id: jump, type: goto_mr, config: {target: "Normal"}}
    edges: [{from: greet, branch: Unclassified, to: jump}]
  - name: "Normal"
    nodes:
      - {id: n1, type: talk, prompt: "hi"}
      - {id: n2, type: exit, prompt: "bye"}
    edges: [{from: n1, branch: Unclassified, to: n2}]
"""


def test_goto_mr_target_must_be_multi_round():
    """goto_mr targeting a non-multi-round canvas raises ManifestError at build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_path.write_text(INVALID_MANIFEST_NON_MR_TARGET, encoding="utf-8")
        out_path = Path(tmpdir) / "speech.json"

        # Should raise ManifestError because "Normal" is not a multi_round target
        with pytest.raises((ManifestError, ValueError)):
            compile_manifest(manifest_path, out_path)
