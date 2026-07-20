"""Tests for tools/registry.py (Task 12).

Step 1: failing tests (RED).
Step 4: should pass after implementation (GREEN).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure dashboard/backend is importable
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from tools import registry  # noqa: E402


# ---------------------------------------------------------------------------
# tool_specs
# ---------------------------------------------------------------------------

def test_specs_include_core_tools():
    names = {t.name for t in registry.tool_specs()}
    assert {"validate", "summarize", "read_node", "apply_mods"} <= names


def test_specs_returns_list_of_tool_spec():
    from llm.base import ToolSpec
    specs = registry.tool_specs()
    assert isinstance(specs, list)
    assert all(isinstance(s, ToolSpec) for s in specs)


def test_specs_have_all_tools():
    names = {t.name for t in registry.tool_specs()}
    expected = {"validate", "summarize", "read_node", "list_intents", "list_variables", "get_facts",
                "apply_mods", "set_path", "delete_path", "build", "scaffold_bot", "get_schema",
                "get_playbook",
                "list_samples", "get_sample", "get_debt_corpus",
                "add_component", "add_node", "add_intent", "add_variable", "connect_components",
                "add_kb",
                "rename_kb", "set_kb_intents", "add_kb_answer", "edit_kb_answer",
                "remove_kb_answer", "set_kb_multiround", "delete_kb",
                "rewire_edge", "delete_edge", "delete_node", "rename_node", "move_node",
                "complete_component",
                "set_hotwords", "set_intent_training", "set_node_tags",
                "import_intents_xlsx", "import_kb_xlsx"}
    assert names == expected


# ---------------------------------------------------------------------------
# dispatch – read-only tools
# ---------------------------------------------------------------------------

_REAL_EXPORT = Path(__file__).resolve().parent / "fixtures" / "sample_export.json"
_DATA = json.loads(_REAL_EXPORT.read_text("utf-8"))


def test_dispatch_validate(monkeypatch):
    out = registry.dispatch("validate", {}, {"BizSpeechComponent": "[]"})
    assert "result" in out


def test_dispatch_validate_shape():
    out = registry.dispatch("validate", {}, _DATA)
    assert "result" in out
    assert "proposal" in out
    assert out["proposal"] is None
    assert isinstance(out["result"], list)


def test_dispatch_summarize():
    out = registry.dispatch("summarize", {}, _DATA)
    assert "result" in out
    assert out["proposal"] is None
    assert "components" in out["result"]


def test_dispatch_read_node():
    uuid = "fdce746c-fe23-5a51-a8b6-03654b1624fa"
    out = registry.dispatch("read_node", {"uuid": uuid}, _DATA)
    assert out["proposal"] is None
    assert out["result"] is not None
    assert out["result"]["uuid"] == uuid


def test_dispatch_read_node_unknown():
    out = registry.dispatch("read_node", {"uuid": "00000000-0000-0000-0000-000000000000"}, _DATA)
    assert out["result"] is None
    assert out["proposal"] is None


def test_dispatch_get_facts():
    out = registry.dispatch("get_facts", {"query": "intent"}, _DATA)
    assert out["proposal"] is None
    assert isinstance(out["result"], list)
    assert len(out["result"]) >= 1


# ---------------------------------------------------------------------------
# dispatch – unknown tool
# ---------------------------------------------------------------------------

def test_dispatch_unknown_tool():
    out = registry.dispatch("nonexistent_tool", {}, _DATA)
    assert "error" in out["result"]
    assert out["proposal"] is None


# ---------------------------------------------------------------------------
# dispatch – mutating tools (apply_mods / set_path / delete_path)
# use a trivial no-op that still succeeds to verify proposal shape
# ---------------------------------------------------------------------------

def test_dispatch_apply_mods_invalid_yaml():
    """Bad YAML → ok=False, no proposal."""
    out = registry.dispatch("apply_mods", {"mods_yaml": "not a list: {{"}, _DATA)
    assert out["proposal"] is None
    assert out["result"]["ok"] is False


def test_dispatch_apply_mods_unknown_op():
    """Unknown op → ok=False with known_ops list."""
    import yaml
    mods = yaml.safe_dump([{"op": "no-such-op", "path": "x"}])
    out = registry.dispatch("apply_mods", {"mods_yaml": mods}, _DATA)
    assert out["proposal"] is None
    assert out["result"]["ok"] is False
    assert "known_ops" in out["result"]


# ---------------------------------------------------------------------------
# required-arg guard (truncated tool calls must not crash the turn)
# ---------------------------------------------------------------------------

def test_dispatch_missing_required_arg_returns_error_not_crash():
    # 'build' requires manifest_yaml; a truncated tool call omits it.
    out = registry.dispatch("build", {}, {})
    assert out["proposal"] is None
    assert out["result"]["ok"] is False
    assert "manifest_yaml" in out["result"]["error"]


def test_dispatch_none_required_arg_treated_as_missing():
    out = registry.dispatch("read_node", {"uuid": None}, {})
    assert out["result"]["ok"] is False
    assert "uuid" in out["result"]["error"]


# ---------------------------------------------------------------------------
# list_intents / list_variables
# ---------------------------------------------------------------------------

def test_list_intents_and_variables_tools():
    data = {
        "SpeechIntent": [{"intentName": "Positive", "isInit": 0}],
        "SpeechVariable": [{"name": "Phone", "variableSource": 1},
                           {"name": "PromiseDate", "variableSource": 0}],
    }
    intents = registry.dispatch("list_intents", {}, data)
    variables = registry.dispatch("list_variables", {}, data)
    assert any(i["name"] == "Positive" for i in intents["result"])
    assert intents["proposal"] is None
    vnames = {v["name"]: v["source"] for v in variables["result"]}
    assert vnames == {"Phone": "system", "PromiseDate": "custom"}
    assert variables["proposal"] is None


def test_connect_components_branch_is_not_enum_restricted():
    spec = next(s for s in registry.tool_specs() if s.name == "connect_components")
    branch = spec.parameters["properties"]["branch"]
    assert "enum" not in branch   # custom branches (branch_intents) allowed
