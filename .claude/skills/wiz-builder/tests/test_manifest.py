"""Tests for wizbuilder.manifest — load + validate manifest YAML."""

from __future__ import annotations

import pytest
from wizbuilder.manifest import (
    Canvas,
    CustomIntent,
    CustomVariable,
    Manifest,
    ManifestError,
    Node,
    load_manifest,
)


def test_load_minimal_returns_manifest(fixture_path):
    m = load_manifest(fixture_path("manifest_minimal.yaml"))
    assert isinstance(m, Manifest)
    assert m.name == "Test Bot"
    assert m.branch == "dev"
    assert m.language == "IDN"
    assert m.custom_variables == []
    assert m.custom_intents == []
    assert len(m.canvases) == 1


def test_load_minimal_canvas_structure(fixture_path):
    m = load_manifest(fixture_path("manifest_minimal.yaml"))
    canvas = m.canvases[0]
    assert isinstance(canvas, Canvas)
    assert canvas.name == "1. Greeting"
    assert len(canvas.nodes) == 1
    node = canvas.nodes[0]
    assert isinstance(node, Node)
    assert node.id == "root"
    assert node.label == "Greeting"
    assert node.parent is None


def test_load_attaches_manifest_text(fixture_path):
    """The raw YAML text is available on the Manifest for hashing."""
    m = load_manifest(fixture_path("manifest_minimal.yaml"))
    assert "Test Bot" in m.raw_text
    assert m.raw_text.startswith("name:")


def test_missing_required_field_raises(tmp_path):
    p = tmp_path / "missing_name.yaml"
    p.write_text("branch: dev\nlanguage: IDN\ncanvases: []\n", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "name" in str(exc.value).lower()


def test_invalid_branch_raises(tmp_path):
    p = tmp_path / "bad_branch.yaml"
    p.write_text(
        "name: X\nbranch: staging\nlanguage: IDN\n"
        "canvases:\n  - name: c\n    nodes:\n      - label: L\n        parent: null\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "branch" in str(exc.value).lower()


def test_canvases_empty_list_raises(tmp_path):
    p = tmp_path / "no_canvas.yaml"
    p.write_text("name: X\nbranch: dev\nlanguage: IDN\ncanvases: []\n", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "canvas" in str(exc.value).lower()


def test_canvas_with_no_nodes_raises(tmp_path):
    p = tmp_path / "empty_canvas.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "canvases:\n  - name: c\n    nodes: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "node" in str(exc.value).lower()


def test_canvas_with_no_root_raises(tmp_path):
    """Every canvas must have at least one node with parent: null."""
    p = tmp_path / "no_root.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "canvases:\n  - name: c\n    nodes:\n      - id: a\n        label: L\n        parent: b\n"
        "      - id: b\n        label: M\n        parent: a\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "root" in str(exc.value).lower()


def test_cross_canvas_parent_ref_raises(fixture_path):
    with pytest.raises(ManifestError) as exc:
        load_manifest(fixture_path("manifest_invalid_cross_canvas.yaml"))
    msg = str(exc.value).lower()
    assert "parent" in msg
    assert "cross-canvas" in msg or "same canvas" in msg


def test_duplicate_canvas_name_raises(tmp_path):
    p = tmp_path / "dup_canvas.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "canvases:\n"
        "  - name: same\n    nodes:\n      - label: L\n        parent: null\n"
        "  - name: same\n    nodes:\n      - label: M\n        parent: null\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "duplicate" in str(exc.value).lower() or "unique" in str(exc.value).lower()


def test_duplicate_variable_name_raises(tmp_path):
    p = tmp_path / "dup_var.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "custom_variables:\n  - name: A\n  - name: A\n"
        "canvases:\n  - name: c\n    nodes:\n      - label: L\n        parent: null\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "duplicate" in str(exc.value).lower()


def test_invalid_variable_name_pattern_raises(tmp_path):
    """Variable names must match [A-Za-z_][A-Za-z0-9_]*."""
    p = tmp_path / "bad_var_name.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "custom_variables:\n  - name: \"1starts-with-digit\"\n"
        "canvases:\n  - name: c\n    nodes:\n      - label: L\n        parent: null\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_custom_variable_loaded(tmp_path):
    p = tmp_path / "with_var.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "custom_variables:\n  - name: CLIENT_NAME\n"
        "canvases:\n  - name: c\n    nodes:\n      - label: L\n        parent: null\n",
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.custom_variables == [CustomVariable(name="CLIENT_NAME")]


def test_custom_intent_loaded(tmp_path):
    p = tmp_path / "with_intent.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "custom_intents:\n"
        "  - name: AskExtension\n    language: IDN\n    keywords: [\"bisa tunda\"]\n"
        "canvases:\n  - name: c\n    nodes:\n      - label: L\n        parent: null\n",
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert len(m.custom_intents) == 1
    i = m.custom_intents[0]
    assert isinstance(i, CustomIntent)
    assert i.name == "AskExtension"
    assert i.language == "IDN"
    assert i.keywords == ("bisa tunda",)
    assert i.user_responses == ()


def test_node_id_auto_generated_when_missing(tmp_path):
    """A node without explicit id gets a synthesized id (e.g., 'node-0')."""
    p = tmp_path / "no_id.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "canvases:\n  - name: c\n    nodes:\n      - label: L\n        parent: null\n",
        encoding="utf-8",
    )
    m = load_manifest(p)
    node = m.canvases[0].nodes[0]
    assert node.id  # non-empty


def test_parse_failure_raises_manifest_error(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("name: X\n  branch: dev\n: : invalid", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "yaml" in str(exc.value).lower() or "parse" in str(exc.value).lower()
