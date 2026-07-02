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
    assert m.custom_variables == ()
    assert m.custom_intents == ()
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
    assert node.prompt == "Greeting"
    assert canvas.edges == ()


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
        "canvases:\n  - name: c\n    nodes:\n      - id: root\n        prompt: L\n",
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


def test_canvas_with_no_entry_raises(tmp_path):
    """A canvas where every node has an incoming edge has no entry node."""
    p = tmp_path / "no_entry.yaml"
    # Both nodes have incoming edges → no entry node → ManifestError
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "canvases:\n  - name: c\n    nodes:\n"
        "      - id: a\n        prompt: L\n"
        "      - id: b\n        prompt: M\n"
        "    edges:\n"
        "      - {from: a, branch: Unclassified, to: b}\n"
        "      - {from: b, branch: Positive, to: a}\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="exactly one entry"):
        load_manifest(p)


def test_cross_canvas_edge_ref_raises(fixture_path):
    """An edge referencing a node id from a different canvas is rejected."""
    with pytest.raises(ManifestError) as exc:
        load_manifest(fixture_path("manifest_invalid_cross_canvas.yaml"))
    msg = str(exc.value).lower()
    assert "unknown" in msg or "destination" in msg or "source" in msg


def test_duplicate_canvas_name_raises(tmp_path):
    p = tmp_path / "dup_canvas.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "canvases:\n"
        "  - name: same\n    nodes:\n      - id: a\n        prompt: L\n"
        "  - name: same\n    nodes:\n      - id: b\n        prompt: M\n",
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
        "canvases:\n  - name: c\n    nodes:\n      - id: root\n        prompt: L\n",
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
        "canvases:\n  - name: c\n    nodes:\n      - id: root\n        prompt: L\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_custom_variable_loaded(tmp_path):
    p = tmp_path / "with_var.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "custom_variables:\n  - name: CLIENT_NAME\n"
        "canvases:\n  - name: c\n    nodes:\n      - id: root\n        prompt: L\n",
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.custom_variables == (CustomVariable(name="CLIENT_NAME"),)


def test_custom_intent_loaded(tmp_path):
    p = tmp_path / "with_intent.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "custom_intents:\n"
        "  - name: AskExtension\n    language: IDN\n    keywords: [\"bisa tunda\"]\n"
        "canvases:\n  - name: c\n    nodes:\n      - id: root\n        prompt: L\n",
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


def test_node_id_required_by_schema(tmp_path):
    """Node `id` is mandatory (required by schema); no auto-synthesis."""
    p = tmp_path / "with_explicit_id.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "canvases:\n  - name: c\n    nodes:\n      - id: root\n        prompt: L\n",
        encoding="utf-8",
    )
    m = load_manifest(p)
    node = m.canvases[0].nodes[0]
    assert node.id == "root"


def test_empty_node_id_raises(tmp_path):
    """An explicit empty-string id is rejected by the schema (not silently auto-filled)."""
    p = tmp_path / "empty_id.yaml"
    p.write_text(
        "name: X\nbranch: dev\nlanguage: IDN\n"
        "canvases:\n  - name: c\n    nodes:\n"
        "      - id: \"\"\n        prompt: L\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_parse_failure_raises_manifest_error(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("name: X\n  branch: dev\n: : invalid", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "yaml" in str(exc.value).lower() or "parse" in str(exc.value).lower()


def test_manifest_schema_language_enum_matches_facts():
    """The static schema enum must stay in sync with facts lang.supported."""
    from pathlib import Path as _Path

    import yaml as _yaml
    from wizfacts import load_facts

    schema_path = (
        _Path(__file__).resolve().parents[1] / "schema" / "manifest.schema.yaml"
    )
    schema = _yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    enum = set(schema["properties"]["language"]["enum"])
    assert enum == set(load_facts().get("lang.supported"))


def test_manifest_accepts_thai(tmp_path):
    from wizbuilder.manifest import load_manifest
    body = (
        "name: T\nbranch: dev\nlanguage: THA\n"
        "canvases:\n  - name: C\n    nodes:\n      - id: root\n        prompt: Greeting\n"
    )
    p = tmp_path / "m.yaml"
    p.write_text(body, encoding="utf-8")
    m = load_manifest(p)
    assert m.language == "THA"


# ---------------------------------------------------------------------------
# New tests: prompt + edges model (Step 1 — written before implementation)
# ---------------------------------------------------------------------------

def _write(tmp_path, text):
    p = tmp_path / "m.yaml"
    p.write_text(text, encoding="utf-8")
    return p


GOOD = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Greeting"
    nodes:
      - {id: greet, prompt: "Halo"}
      - {id: bye, prompt: "Terima kasih"}
    edges:
      - {from: greet, branch: Unclassified, to: bye}
"""


def test_loads_prompt_and_edges(tmp_path):
    m = load_manifest(_write(tmp_path, GOOD))
    c = m.canvases[0]
    assert [n.prompt for n in c.nodes] == ["Halo", "Terima kasih"]
    assert (c.edges[0].src, c.edges[0].branch, c.edges[0].dst) == ("greet", "Unclassified", "bye")


def test_rejects_two_entry_nodes(tmp_path):
    """Two nodes with no incoming edges → not exactly one entry → ManifestError."""
    # Remove the entire edges block so both nodes have no incoming edge
    txt = GOOD.replace(
        "    edges:\n      - {from: greet, branch: Unclassified, to: bye}\n", ""
    )
    with pytest.raises(ManifestError, match="exactly one entry"):
        load_manifest(_write(tmp_path, txt))


def test_rejects_bad_branch(tmp_path):
    """An edge with a branch name outside the 5 allowed names is rejected."""
    with pytest.raises(ManifestError):
        load_manifest(_write(tmp_path, GOOD.replace("Unclassified", "Sideways")))


def test_rejects_unknown_edge_endpoint(tmp_path):
    """An edge referencing a node id not declared in the canvas is rejected."""
    bad = GOOD.replace("to: bye", "to: ghost")
    with pytest.raises(ManifestError):
        load_manifest(_write(tmp_path, bad))


def test_rejects_duplicate_src_branch(tmp_path):
    """Two edges with the same (from, branch) pair are rejected."""
    dup = GOOD.replace(
        "      - {from: greet, branch: Unclassified, to: bye}",
        "      - {from: greet, branch: Unclassified, to: bye}\n"
        "      - {from: greet, branch: Unclassified, to: bye}",
    )
    with pytest.raises(ManifestError):
        load_manifest(_write(tmp_path, dup))


def test_single_node_canvas_is_valid(tmp_path):
    """A single-node canvas with no edges is valid — that node is the entry."""
    single = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Greeting"
    nodes:
      - {id: greet, prompt: "Halo"}
"""
    m = load_manifest(_write(tmp_path, single))
    assert len(m.canvases[0].nodes) == 1
    assert m.canvases[0].edges == ()


def test_no_answer_branch_accepted(tmp_path):
    """'No answer' (with space) is a valid branch name."""
    txt = GOOD.replace("Unclassified", "No answer")
    m = load_manifest(_write(tmp_path, txt))
    assert m.canvases[0].edges[0].branch == "No answer"


def test_node_type_talk_accepted(tmp_path):
    """Explicit type: talk is accepted and round-trips through the dataclass."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Greeting"
    nodes:
      - {id: greet, prompt: "Halo", type: talk}
"""
    m = load_manifest(_write(tmp_path, txt))
    assert m.canvases[0].nodes[0].type == "talk"


def test_node_unknown_type_rejected(tmp_path):
    """A node with type not in the schema enum must be rejected."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Greeting"
    nodes:
      - {id: greet, prompt: "Halo", type: bogus}
"""
    with pytest.raises(ManifestError):
        load_manifest(_write(tmp_path, txt))


def test_node_config_accepted(tmp_path):
    """Optional config object is accepted and round-trips."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Greeting"
    nodes:
      - id: greet
        prompt: "Halo"
        config:
          foo: bar
"""
    m = load_manifest(_write(tmp_path, txt))
    assert m.canvases[0].nodes[0].config == {"foo": "bar"}


# ---------------------------------------------------------------------------
# Task-1 (exit/goto plan): exit, transfer, goto node-type tests
# ---------------------------------------------------------------------------


def test_exit_node_accepted_valid(tmp_path):
    """A canvas with a Talk entry → exit node (connected by edge) loads OK; type preserved."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo", type: talk}
      - {id: bye, prompt: "Sampai jumpa", type: exit}
    edges:
      - {from: greet, branch: Unclassified, to: bye}
"""
    m = load_manifest(_write(tmp_path, txt))
    nodes = {n.id: n for n in m.canvases[0].nodes}
    assert nodes["greet"].type == "talk"
    assert nodes["bye"].type == "exit"


def test_transfer_node_accepted_valid(tmp_path):
    """A transfer node is accepted and its type round-trips."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - {id: transfer, prompt: "Connecting you", type: transfer}
    edges:
      - {from: greet, branch: Unclassified, to: transfer}
"""
    m = load_manifest(_write(tmp_path, txt))
    nodes = {n.id: n for n in m.canvases[0].nodes}
    assert nodes["transfer"].type == "transfer"


def test_goto_node_accepted_valid(tmp_path):
    """2-canvas manifest: canvas A goto node with config.target = canvas B name — loads OK."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - id: jump
        prompt: "Redirecting"
        type: goto
        config:
          target: "2. Follow-up"
    edges:
      - {from: greet, branch: Unclassified, to: jump}
  - name: "2. Follow-up"
    nodes:
      - {id: followup, prompt: "Follow-up response"}
"""
    m = load_manifest(_write(tmp_path, txt))
    nodes_a = {n.id: n for n in m.canvases[0].nodes}
    assert nodes_a["jump"].type == "goto"
    assert nodes_a["jump"].config["target"] == "2. Follow-up"


def test_goto_missing_config_target_rejected(tmp_path):
    """A goto node with no config.target is rejected."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - {id: jump, prompt: "Redirecting", type: goto}
    edges:
      - {from: greet, branch: Unclassified, to: jump}
  - name: "2. Follow-up"
    nodes:
      - {id: followup, prompt: "Follow-up"}
"""
    with pytest.raises(ManifestError, match="config.target"):
        load_manifest(_write(tmp_path, txt))


def test_goto_unknown_target_rejected(tmp_path):
    """A goto node whose config.target names a non-existent canvas is rejected."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - id: jump
        prompt: "Redirecting"
        type: goto
        config:
          target: "3. NonExistent"
    edges:
      - {from: greet, branch: Unclassified, to: jump}
  - name: "2. Follow-up"
    nodes:
      - {id: followup, prompt: "Follow-up"}
"""
    with pytest.raises(ManifestError, match="config.target"):
        load_manifest(_write(tmp_path, txt))


def test_exit_node_with_outgoing_edge_rejected(tmp_path):
    """An exit node with an outgoing edge is rejected (terminal rule)."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - {id: bye, prompt: "Bye", type: exit}
      - {id: extra, prompt: "Extra"}
    edges:
      - {from: greet, branch: Unclassified, to: bye}
      - {from: bye, branch: Positive, to: extra}
"""
    with pytest.raises(ManifestError, match="terminal"):
        load_manifest(_write(tmp_path, txt))


def test_transfer_node_with_outgoing_edge_rejected(tmp_path):
    """A transfer node with an outgoing edge is rejected (terminal rule)."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - {id: tx, prompt: "Transfer", type: transfer}
      - {id: extra, prompt: "Extra"}
    edges:
      - {from: greet, branch: Unclassified, to: tx}
      - {from: tx, branch: Positive, to: extra}
"""
    with pytest.raises(ManifestError, match="terminal"):
        load_manifest(_write(tmp_path, txt))


def test_goto_node_with_outgoing_edge_rejected(tmp_path):
    """A goto node with an outgoing edge is rejected (terminal rule)."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - id: jump
        prompt: "Redirect"
        type: goto
        config:
          target: "2. Follow-up"
      - {id: extra, prompt: "Extra"}
    edges:
      - {from: greet, branch: Unclassified, to: jump}
      - {from: jump, branch: Positive, to: extra}
  - name: "2. Follow-up"
    nodes:
      - {id: followup, prompt: "Follow-up"}
"""
    with pytest.raises(ManifestError, match="terminal"):
        load_manifest(_write(tmp_path, txt))


def test_goto_self_targeting_rejected(tmp_path):
    """A goto node whose config.target names its OWN canvas is rejected (must be another)."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - id: jump
        prompt: "Loop"
        type: goto
        config:
          target: "1. Main"
    edges:
      - {from: greet, branch: Unclassified, to: jump}
  - name: "2. Other"
    nodes:
      - {id: other, prompt: "Other"}
"""
    with pytest.raises(ManifestError, match="does not match any other canvas"):
        load_manifest(_write(tmp_path, txt))


# ---------------------------------------------------------------------------
# Task 1 (conditional/assign): new node types + silent-node prompt default
# ---------------------------------------------------------------------------

_OPS = {">", ">=", "<", "<=", "=", "!=", "In", "NotIn", "IsNull", "NotNull", "Contains"}


def test_conditional_and_assign_load(tmp_path):
    m = load_manifest(_write(tmp_path, """
name: Cond Bot
branch: dev
language: IDN
custom_variables:
  - {name: Gender}
  - {name: Salutation}
canvases:
  - name: Greet
    nodes:
      - {id: cond, type: conditional, config: {variable: Gender, branches: [
          {name: Bapak, op: "=", value: Male, to: set_b},
          {name: Bapak, op: "=", value: M, to: set_b},
          {name: Ibu, op: In, value: "F,Female", to: set_i},
          {name: Default, to: set_b}]}}
      - {id: set_b, type: assign, config: {variable: Salutation, value: Bapak}}
      - {id: set_i, type: assign, config: {variable: Salutation, value: Ibu}}
    edges:
      - {from: set_b, branch: Default, to: set_i}
"""))
    canvas = m.canvases[0]
    cond = next(n for n in canvas.nodes if n.id == "cond")
    assert cond.type == "conditional"
    assert cond.prompt == ""  # silent node: prompt optional
    assert len(cond.config["branches"]) == 4
    set_i = next(n for n in canvas.nodes if n.id == "set_i")
    assert set_i.type == "assign" and set_i.config["value"] == "Ibu"


def test_conditional_undeclared_variable_rejected(tmp_path):
    with pytest.raises(ManifestError, match="not a declared variable"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
canvases:
  - name: C
    nodes:
      - {id: cond, type: conditional, config: {variable: Ghost, branches: [
          {name: A, op: "=", value: x, to: t}, {name: Default, to: t}]}}
      - {id: t, type: assign, config: {variable: Ghost, value: y}}
"""))


def test_conditional_requires_exactly_one_default(tmp_path):
    with pytest.raises(ManifestError, match="exactly one Default"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
custom_variables: [{name: G}]
canvases:
  - name: C
    nodes:
      - {id: cond, type: conditional, config: {variable: G, branches: [
          {name: A, op: "=", value: x, to: t}]}}
      - {id: t, type: assign, config: {variable: G, value: y}}
"""))


def test_conditional_same_name_conflicting_target_rejected(tmp_path):
    with pytest.raises(ManifestError, match="conflicting target"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
custom_variables: [{name: G}]
canvases:
  - name: C
    nodes:
      - {id: cond, type: conditional, config: {variable: G, branches: [
          {name: A, op: "=", value: x, to: t1},
          {name: A, op: "=", value: y, to: t2},
          {name: Default, to: t1}]}}
      - {id: t1, type: assign, config: {variable: G, value: a}}
      - {id: t2, type: assign, config: {variable: G, value: b}}
"""))


def test_conditional_bad_operator_rejected(tmp_path):
    with pytest.raises(ManifestError, match="invalid operator"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
custom_variables: [{name: G}]
canvases:
  - name: C
    nodes:
      - {id: cond, type: conditional, config: {variable: G, branches: [
          {name: A, op: "~~", value: x, to: t}, {name: Default, to: t}]}}
      - {id: t, type: assign, config: {variable: G, value: y}}
"""))


def test_conditional_branch_target_must_exist(tmp_path):
    with pytest.raises(ManifestError, match="unknown target"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
custom_variables: [{name: G}]
canvases:
  - name: C
    nodes:
      - {id: cond, type: conditional, config: {variable: G, branches: [
          {name: A, op: "=", value: x, to: ghost}, {name: Default, to: cond}]}}
"""))


def test_value_and_value_var_mutually_exclusive(tmp_path):
    with pytest.raises(ManifestError, match="exactly one of value/value_var"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
custom_variables: [{name: G}, {name: H}]
canvases:
  - name: C
    nodes:
      - {id: cond, type: conditional, config: {variable: G, branches: [
          {name: A, op: "=", value: x, value_var: H, to: t}, {name: Default, to: t}]}}
      - {id: t, type: assign, config: {variable: G, value: y}}
"""))


def test_unary_op_takes_no_operand(tmp_path):
    # IsNull/NotNull are valid with neither value nor value_var
    m = load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
custom_variables: [{name: G}]
canvases:
  - name: C
    nodes:
      - {id: cond, type: conditional, config: {variable: G, branches: [
          {name: A, op: IsNull, to: t}, {name: Default, to: t}]}}
      - {id: t, type: assign, config: {variable: G, value: y}}
"""))
    assert m.canvases[0].nodes[0].config["branches"][0]["op"] == "IsNull"


def test_assign_undeclared_variable_rejected(tmp_path):
    """An assign node whose config.variable is not in custom_variables is rejected."""
    with pytest.raises(ManifestError, match="not a declared variable"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
custom_variables: [{name: Declared}]
canvases:
  - name: C
    nodes:
      - {id: cond, type: conditional, config: {variable: Declared, branches: [
          {name: A, op: "=", value: x, to: t}, {name: Default, to: t}]}}
      - {id: t, type: assign, config: {variable: Undeclared, value: y}}
"""))


def test_default_branch_rejected_on_talk_edge(tmp_path):
    """Default is not a valid branch for an edge whose source is a talk node."""
    with pytest.raises(ManifestError):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
canvases:
  - name: C
    nodes:
      - {id: greet, prompt: "Halo", type: talk}
      - {id: bye, prompt: "Bye", type: talk}
    edges:
      - {from: greet, branch: Default, to: bye}
"""))


# ---------------------------------------------------------------------------
# NC-Task 1 (nested + exit_port): new node types
# ---------------------------------------------------------------------------


def test_nested_and_exit_port_load(tmp_path):
    m = load_manifest(_write(tmp_path, """
name: Nest Bot
branch: dev
language: IDN
canvases:
  - name: Parent
    nodes:
      - {id: open, prompt: "Halo"}
      - {id: sub, type: nested, config: {target: Child}}
      - {id: bye_yes, type: exit, prompt: "Ya"}
      - {id: bye_no, type: exit, prompt: "Tidak"}
    edges:
      - {from: open, branch: Unclassified, to: sub}
      - {from: sub, branch: "Yes", to: bye_yes}
      - {from: sub, branch: "No", to: bye_no}
  - name: Child
    nodes:
      - {id: ask, prompt: "Setuju?"}
      - {id: ex_yes, type: exit_port, config: {name: "Yes"}}
      - {id: ex_no, type: exit_port, config: {name: "No"}}
    edges:
      - {from: ask, branch: Positive, to: ex_yes}
      - {from: ask, branch: Negative, to: ex_no}
"""))
    parent = next(c for c in m.canvases if c.name == "Parent")
    sub = next(n for n in parent.nodes if n.id == "sub")
    assert sub.type == "nested" and sub.config["target"] == "Child"
    child = next(c for c in m.canvases if c.name == "Child")
    assert {n.config["name"] for n in child.nodes if n.type == "exit_port"} == {"Yes", "No"}


def test_nested_unknown_target_rejected(tmp_path):
    with pytest.raises(ManifestError, match="does not match any other canvas"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
canvases:
  - name: Parent
    nodes:
      - {id: open, prompt: "Hi"}
      - {id: sub, type: nested, config: {target: Ghost}}
    edges: [{from: open, branch: Unclassified, to: sub}]
"""))


def test_child_must_have_exit_port(tmp_path):
    with pytest.raises(ManifestError, match="must contain at least one exit_port"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
canvases:
  - name: Parent
    nodes: [{id: open, prompt: Hi}, {id: sub, type: nested, config: {target: Child}}]
    edges: [{from: open, branch: Unclassified, to: sub}]
  - name: Child
    nodes: [{id: ask, prompt: Q}]
"""))


def test_nested_branch_must_match_child_exit(tmp_path):
    with pytest.raises(ManifestError, match="no exit_port named"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
canvases:
  - name: Parent
    nodes: [{id: open, prompt: Hi}, {id: sub, type: nested, config: {target: Child}}, {id: bye, type: exit, prompt: Bye}]
    edges: [{from: open, branch: Unclassified, to: sub}, {from: sub, branch: Maybe, to: bye}]
  - name: Child
    nodes: [{id: ask, prompt: Q}, {id: ex, type: exit_port, config: {name: "Yes"}}]
    edges: [{from: ask, branch: Positive, to: ex}]
"""))


def test_exit_port_terminal_no_outgoing(tmp_path):
    with pytest.raises(ManifestError, match="terminal"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
canvases:
  - name: Parent
    nodes: [{id: open, prompt: Hi}, {id: sub, type: nested, config: {target: Child}}, {id: bye, type: exit, prompt: B}]
    edges: [{from: open, branch: Unclassified, to: sub}, {from: sub, branch: "Yes", to: bye}]
  - name: Child
    nodes: [{id: ask, prompt: Q}, {id: ex, type: exit_port, config: {name: "Yes"}}, {id: ask2, prompt: Q2}]
    edges: [{from: ask, branch: Positive, to: ex}, {from: ex, branch: Positive, to: ask2}]
"""))


def test_child_referenced_by_two_nested_rejected(tmp_path):
    with pytest.raises(ManifestError, match="referenced by more than one"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
canvases:
  - name: Parent
    nodes: [{id: open, prompt: Hi}, {id: s1, type: nested, config: {target: Child}}, {id: s2, type: nested, config: {target: Child}}, {id: bye, type: exit, prompt: B}]
    edges: [{from: open, branch: Unclassified, to: s1}, {from: s1, branch: "Yes", to: s2}, {from: s2, branch: "Yes", to: bye}]
  - name: Child
    nodes: [{id: ask, prompt: Q}, {id: ex, type: exit_port, config: {name: "Yes"}}]
    edges: [{from: ask, branch: Positive, to: ex}]
"""))


def test_stray_exit_port_canvas_rejected(tmp_path):
    """M1: a canvas with exit_port nodes that is NOT targeted by any nested node must raise
    ManifestError matching 'only valid in a nested child canvas'.
    """
    with pytest.raises(ManifestError, match="only valid in a nested child canvas"):
        load_manifest(_write(tmp_path, """
name: B
branch: dev
language: IDN
canvases:
  - name: Main
    nodes: [{id: open, prompt: Hi}, {id: bye, type: exit, prompt: Bye}]
    edges: [{from: open, branch: Positive, to: bye}]
  - name: Orphan
    nodes: [{id: ep1, type: exit_port, config: {name: "Done"}}]
"""))


# ---------------------------------------------------------------------------
# KB-T1: knowledge_bases manifest surface + validation
# ---------------------------------------------------------------------------

from wizbuilder.manifest import KnowledgeBase  # noqa: E402


def test_knowledge_bases_load(tmp_path):
    m = load_manifest(_write(tmp_path, """
name: KB Bot
branch: dev
language: IDN
custom_intents:
  - {name: "Due Q", language: IDN}
canvases:
  - name: Flow
    nodes: [{id: greet, prompt: "Halo"}]
  - name: Handler
    nodes: [{id: h_greet, prompt: "Handler greeting"}]
knowledge_bases:
  - {name: "Due date", intents: ["Due Q"], answers: ["Jatuh tempo tanggal 25."]}
  - {name: "Special case", intents: ["Due Q"], answers: ["Baik."], multi_round: "Handler"}
"""))
    kbs = {k.name: k for k in m.knowledge_bases}
    assert len(m.knowledge_bases) == 2
    assert isinstance(kbs["Due date"], KnowledgeBase)
    assert kbs["Due date"].intents == ("Due Q",)
    assert kbs["Due date"].answers == ("Jatuh tempo tanggal 25.",)
    assert kbs["Due date"].multi_round is None
    assert kbs["Special case"].multi_round == "Handler"


def test_knowledge_bases_empty_by_default(tmp_path):
    """A manifest with no knowledge_bases key parses to an empty tuple."""
    m = load_manifest(_write(tmp_path, """
name: T
branch: dev
language: IDN
canvases:
  - name: C
    nodes: [{id: root, prompt: Hi}]
"""))
    assert m.knowledge_bases == ()


def test_kb_undeclared_intent_rejected(tmp_path):
    """A KB referencing an intent name not in custom_intents is rejected."""
    with pytest.raises(ManifestError, match="not a declared"):
        load_manifest(_write(tmp_path, """
name: KB Bot
branch: dev
language: IDN
custom_intents:
  - {name: "Real Intent", language: IDN}
canvases:
  - name: Flow
    nodes: [{id: greet, prompt: "Halo"}]
knowledge_bases:
  - {name: "Due date", intents: ["Ghost Intent"], answers: ["Answer."]}
"""))


def test_kb_unknown_multiround_target_rejected(tmp_path):
    """A KB multi_round naming a canvas that does not exist is rejected."""
    with pytest.raises(ManifestError, match="multi_round target"):
        load_manifest(_write(tmp_path, """
name: KB Bot
branch: dev
language: IDN
custom_intents:
  - {name: "Due Q", language: IDN}
canvases:
  - name: Flow
    nodes: [{id: greet, prompt: "Halo"}]
knowledge_bases:
  - {name: "Due date", intents: ["Due Q"], answers: ["Ans."], multi_round: "NonExistent"}
"""))


def test_kb_needs_answer_or_multiround(tmp_path):
    """A KB with no answers and no multi_round is rejected."""
    with pytest.raises(ManifestError, match="at least one answer"):
        load_manifest(_write(tmp_path, """
name: KB Bot
branch: dev
language: IDN
custom_intents:
  - {name: "Due Q", language: IDN}
canvases:
  - name: Flow
    nodes: [{id: greet, prompt: "Halo"}]
knowledge_bases:
  - {name: "Due date", intents: ["Due Q"]}
"""))


def test_kb_duplicate_name_rejected(tmp_path):
    """Two KBs with the same name are rejected."""
    with pytest.raises(ManifestError, match="duplicate knowledge base"):
        load_manifest(_write(tmp_path, """
name: KB Bot
branch: dev
language: IDN
custom_intents:
  - {name: "Due Q", language: IDN}
canvases:
  - name: Flow
    nodes: [{id: greet, prompt: "Halo"}]
knowledge_bases:
  - {name: "Due date", intents: ["Due Q"], answers: ["Answer 1."]}
  - {name: "Due date", intents: ["Due Q"], answers: ["Answer 2."]}
"""))


def test_kb_multiround_only_valid(tmp_path):
    """A KB with multi_round but no answers is valid (multi_round counts as the answer target)."""
    m = load_manifest(_write(tmp_path, """
name: KB Bot
branch: dev
language: IDN
custom_intents:
  - {name: "Due Q", language: IDN}
canvases:
  - name: Flow
    nodes: [{id: greet, prompt: "Halo"}]
  - name: Handler
    nodes: [{id: h, prompt: "Handler"}]
knowledge_bases:
  - {name: "Delegated", intents: ["Due Q"], multi_round: "Handler"}
"""))
    kb = m.knowledge_bases[0]
    assert kb.name == "Delegated"
    assert kb.answers == ()
    assert kb.multi_round == "Handler"


# ---------------------------------------------------------------------------
# Task 3: talk_goto node type validation
# ---------------------------------------------------------------------------


def test_talk_goto_requires_target_and_prompt(tmp_path):
    """talk_goto requires config.target (another canvas) + non-empty prompt."""
    good = """
name: T
branch: dev
language: IDN
canvases:
  - name: A
    nodes:
      - {id: n1, type: talk_goto, prompt: "bye", config: {target: B}}
    edges: []
  - name: B
    nodes:
      - {id: b1, type: talk, prompt: "hi"}
      - {id: b2, type: exit, prompt: "end"}
    edges: [{from: b1, branch: Unclassified, to: b2}]
"""
    load_manifest(_write(tmp_path, good))  # must not raise

    bad = good.replace("config: {target: B}", "config: {}")
    with pytest.raises(ManifestError):
        load_manifest(_write(tmp_path, bad))


def test_talk_goto_unknown_target_rejected(tmp_path):
    """A talk_goto node whose config.target names a non-existent canvas is rejected."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - id: jump
        prompt: "Redirecting"
        type: talk_goto
        config:
          target: "3. NonExistent"
    edges:
      - {from: greet, branch: Unclassified, to: jump}
  - name: "2. Follow-up"
    nodes:
      - {id: followup, prompt: "Follow-up"}
"""
    with pytest.raises(ManifestError, match="config.target"):
        load_manifest(_write(tmp_path, txt))


def test_talk_goto_self_targeting_rejected(tmp_path):
    """A talk_goto node whose config.target names its OWN canvas is rejected (must be another)."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - id: jump
        prompt: "Loop"
        type: talk_goto
        config:
          target: "1. Main"
    edges:
      - {from: greet, branch: Unclassified, to: jump}
  - name: "2. Other"
    nodes:
      - {id: other, prompt: "Other"}
"""
    with pytest.raises(ManifestError, match="does not match any other canvas"):
        load_manifest(_write(tmp_path, txt))


def test_talk_goto_node_with_outgoing_edge_rejected(tmp_path):
    """A talk_goto node with an outgoing edge is rejected (terminal rule)."""
    txt = """
name: T
branch: dev
language: IDN
canvases:
  - name: "1. Main"
    nodes:
      - {id: greet, prompt: "Halo"}
      - id: jump
        prompt: "Redirect"
        type: talk_goto
        config:
          target: "2. Follow-up"
      - {id: extra, prompt: "Extra"}
    edges:
      - {from: greet, branch: Unclassified, to: jump}
      - {from: jump, branch: Positive, to: extra}
  - name: "2. Follow-up"
    nodes:
      - {id: followup, prompt: "Follow-up"}
"""
    with pytest.raises(ManifestError, match="terminal"):
        load_manifest(_write(tmp_path, txt))
