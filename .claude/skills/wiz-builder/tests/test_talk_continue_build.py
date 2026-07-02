"""Test builder serializer for talk_continue (type 5) nodes."""

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
name: TalkContinue Demo
branch: dev
language: IDN
knowledge_bases:
  - name: "K1"
    intents: ["Intent1"]
    answers: ["hai"]
    multi_round: "MR A"
custom_intents:
  - name: "Intent1"
    language: IDN
    keywords: ["x"]
    user_responses: ["y"]
canvases:
  - name: "Main"
    nodes:
      - {id: greet, type: talk, prompt: "halo"}
      - {id: greet_exit, type: exit, prompt: "bye"}
    edges: [{from: greet, branch: Unclassified, to: greet_exit}]
  - name: "MR A"
    nodes:
      - {id: mr1, type: talk, prompt: "putaran A"}
      - {id: tc, type: talk_continue, prompt: "Baik, saya tunggu jawaban Anda."}
    edges: [{from: mr1, branch: Unclassified, to: tc}]
"""


def test_talk_continue_builds_type5_clean():
    """talk_continue inside MR A compiles to type 5 node with empty routes, no SCS, no topFloor."""
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

    # WIZ107 regression: a component whose only terminal is a talk_continue must NOT be
    # flagged "no terminal" (talk_continue is terminal). MR A ends in talk_continue.
    assert not [f for f in all_findings if f.code == "WIZ107"], \
        "talk_continue must satisfy the component-has-terminal check (WIZ107)"

    # Find the type-5 node in the MR A component
    comps = unwrap(data["BizSpeechComponent"])
    mr_a_comp = None
    for c in comps:
        if c.get("name") == "MR A":
            mr_a_comp = c

    assert mr_a_comp, "expected MR A component in the build"

    # Find the type-5 node within MR A
    det = mr_a_comp.get("details")
    tree = json.loads(det) if isinstance(det, str) else det
    found = None
    for n in (tree or {}).values():
        if (n.get("data") or {}).get("type") == 5:
            found = n

    assert found, "expected a type-5 node in MR A component"
    d = found["data"]

    # Verify type 5
    assert d["type"] == 5, f"Expected type 5, got {d['type']}"

    # Verify list contains the prompt
    assert d["list"] == ["Baik, saya tunggu jawaban Anda."], \
        f"Expected list with prompt, got {d['list']!r}"

    # Verify appoint_node_id is empty (no return target)
    assert d["appoint_node_id"] == "", f"appoint_node_id must be empty, got {d['appoint_node_id']!r}"

    # Verify empty routes
    routes = mr_a_comp.get("routes")
    routes = json.loads(routes) if isinstance(routes, str) else routes
    node_routes = routes.get(d["id"], {})
    assert node_routes == {}, f"talk_continue is terminal: routes must be empty, got {node_routes}"

    # Verify no SentenceCutSpeech row for this node
    scs = json.loads(data["SentenceCutSpeech"])
    node_scs = [row for row in scs if row.get("id") == d["id"]]
    assert node_scs == [], f"talk_continue must not emit SentenceCutSpeech row, found {len(node_scs)}"

    # Verify no topFloorDetails row for this node
    comp_top_floor = json.loads(mr_a_comp.get("topFloorDetails", "[]"))
    node_top_floor = [row for row in comp_top_floor if row.get("id") == d["id"]]
    assert node_top_floor == [], f"talk_continue must not emit topFloorDetails row, found {len(node_top_floor)}"

    # Verify MR A is category 2 (multi-round)
    assert mr_a_comp.get("category") == 2, f"MR A should be category 2, got {mr_a_comp.get('category')}"


VALID_MANIFEST_WITH_RETURN = """
name: TalkContinue Return Demo
branch: dev
language: IDN
knowledge_bases:
  - name: "K1"
    intents: ["Intent1"]
    answers: ["hai"]
    multi_round: "MR A"
custom_intents:
  - name: "Intent1"
    language: IDN
    keywords: ["x"]
    user_responses: ["y"]
canvases:
  - name: "Main"
    nodes:
      - {id: greet, type: talk, prompt: "halo"}
      - {id: greet_exit, type: exit, prompt: "bye"}
    edges: [{from: greet, branch: Unclassified, to: greet_exit}]
  - name: "MR A"
    nodes:
      - {id: mr1, type: talk, prompt: "putaran A"}
      - {id: tc, type: talk_continue, prompt: "Tunggu", config: {target: "Main"}}
    edges: [{from: mr1, branch: Unclassified, to: tc}]
"""


def test_talk_continue_with_return_target():
    """talk_continue with config.target resolves the return component UUID and name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_path.write_text(VALID_MANIFEST_WITH_RETURN, encoding="utf-8")
        out_path = Path(tmpdir) / "speech.json"
        compile_manifest(manifest_path, out_path)

        data = json.loads(out_path.read_text(encoding="utf-8"))

    # Check no errors
    all_findings = run_all_checks(parse_dict(data))
    errs = [f for f in all_findings if f.severity.name == "ERROR"]
    assert errs == [], f"Build produced errors: {errs}"

    # Find Main and MR A components
    comps = unwrap(data["BizSpeechComponent"])
    main_comp = None
    mr_a_comp = None
    main_uuid = None
    for c in comps:
        if c.get("name") == "Main":
            main_comp = c
            main_uuid = c.get("componentUuid")
        elif c.get("name") == "MR A":
            mr_a_comp = c

    assert main_comp, "expected Main component"
    assert mr_a_comp, "expected MR A component"
    assert main_uuid, "expected Main component UUID"

    # Find the type-5 node
    det = mr_a_comp.get("details")
    tree = json.loads(det) if isinstance(det, str) else det
    found = None
    for n in (tree or {}).values():
        if (n.get("data") or {}).get("type") == 5:
            found = n

    assert found, "expected a type-5 node in MR A component"
    d = found["data"]

    # Verify appoint_node_id is set to Main's UUID (return target)
    assert d["appoint_node_id"] == main_uuid, \
        f"appoint_node_id should be Main's UUID ({main_uuid}), got {d['appoint_node_id']!r}"

    # Verify specificComponentName is set
    assert d["specificComponentName"] == "Main", \
        f"specificComponentName should be 'Main', got {d['specificComponentName']!r}"


INVALID_MANIFEST_TALK_CONTINUE_IN_NORMAL = """
name: TalkContinue In Normal Canvas
branch: dev
language: IDN
custom_intents:
  - {name: Intent1, language: IDN, keywords: ["x"], user_responses: ["x"]}
knowledge_bases:
  - {name: "K1", intents: ["Intent1"], answers: ["hai"], multi_round: "MR A"}
canvases:
  - name: "Main"
    nodes:
      - {id: tc, type: talk_continue, prompt: "wait"}
    edges: []
  - name: "MR A"
    nodes:
      - {id: a1, type: talk, prompt: "hi"}
      - {id: a2, type: exit, prompt: "bye"}
    edges: [{from: a1, branch: Unclassified, to: a2}]
"""


def test_talk_continue_in_normal_canvas_rejected():
    """talk_continue in a non-multi-round canvas raises ValueError at build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_path.write_text(INVALID_MANIFEST_TALK_CONTINUE_IN_NORMAL, encoding="utf-8")
        out_path = Path(tmpdir) / "speech.json"

        # Should raise ValueError because talk_continue is in "Main" which is not a multi_round target
        with pytest.raises((ManifestError, ValueError), match="only valid inside a multi-round"):
            compile_manifest(manifest_path, out_path)


INVALID_MANIFEST_RETURN_TARGET_MR = """
name: TalkContinue Return To MR
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
      - {id: m, type: talk, prompt: "hi"}
      - {id: m_exit, type: exit, prompt: "bye"}
    edges: [{from: m, branch: Unclassified, to: m_exit}]
  - name: "MR A"
    nodes:
      - {id: a1, type: talk, prompt: "hi2"}
      - {id: tc, type: talk_continue, prompt: "wait", config: {target: "MR B"}}
    edges: [{from: a1, branch: Unclassified, to: tc}]
  - name: "MR B"
    nodes:
      - {id: b1, type: talk, prompt: "hi3"}
      - {id: b2, type: exit, prompt: "bye"}
    edges: [{from: b1, branch: Unclassified, to: b2}]
"""


def test_talk_continue_return_target_must_be_main_flow():
    """talk_continue return target must be a non-multi-round (main-flow) canvas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_path.write_text(INVALID_MANIFEST_RETURN_TARGET_MR, encoding="utf-8")
        out_path = Path(tmpdir) / "speech.json"

        # Should raise ValueError because the return target "MR B" is a multi-round canvas
        with pytest.raises((ManifestError, ValueError), match="must be a main-flow"):
            compile_manifest(manifest_path, out_path)
