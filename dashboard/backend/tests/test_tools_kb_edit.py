"""Task 7: dashboard chat tools for the 7 KB-edit ops.

Mirrors the add_kb dispatch test in test_tools_edit.py — each tool should
produce a proposal (ok=True, proposal dict present) when dispatched with
minimal valid params against a two-component doc that has a KB fixture.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agents
from tools import registry

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def kb_doc():
    """A two-component doc with one user-created KB (FAQ) for testing KB-edit tools.

    KB is added via the add_kb tool (not the manifest) so we can use the
    system intents already present in SpeechIntent after scaffolding.
    """
    # 1. Scaffold baseline
    params = {
        "name": "Test Bot", "language": "IDN", "branch": "dev",
        "canvases": [
            {"name": "1. Greeting", "nodes": [{"id": "open", "prompt": "Halo"}]},
            {"name": "2. Multi", "nodes": [{"id": "open2", "prompt": "Lanjut"}]},
        ],
    }
    r = agents.propose_scaffold(params)
    assert r["ok"], r.get("error")
    base_doc = r["proposed_data"]

    # 2. Add KB via add_kb tool so that Positive (a system intent) resolves
    added = registry.dispatch("add_kb", {
        "name": "FAQ",
        "intents": ["Positive"],
        "answers": ["Ya, kami bisa membantu."],
    }, base_doc)
    assert added["result"]["ok"], f"add_kb fixture failed: {added['result'].get('error')}"
    return added["proposal"]["proposed_data"]


# ---------------------------------------------------------------------------
# Task 7: 7 KB-edit tools registered
# ---------------------------------------------------------------------------

_KB_EDIT_TOOLS = [
    "rename_kb",
    "set_kb_intents",
    "add_kb_answer",
    "edit_kb_answer",
    "remove_kb_answer",
    "set_kb_multiround",
    "delete_kb",
]


def test_kb_edit_tools_registered():
    """tool_specs() must include all seven KB-edit tools."""
    names = {s.name for s in registry.tool_specs()}
    for tool_name in _KB_EDIT_TOOLS:
        assert tool_name in names, f"{tool_name!r} not found in registry"


def test_kb_edit_tool_schemas():
    """Each KB-edit tool must expose the correct parameter schema."""
    specs = {s.name: s for s in registry.tool_specs()}

    # rename_kb: name(str, required), new_name(str, required)
    rk = specs["rename_kb"].parameters
    assert rk["properties"]["name"]["type"] == "string"
    assert rk["properties"]["new_name"]["type"] == "string"
    assert set(rk.get("required", [])) >= {"name", "new_name"}

    # set_kb_intents: name(str, required), intents(array of str, required)
    si = specs["set_kb_intents"].parameters
    assert si["properties"]["name"]["type"] == "string"
    assert si["properties"]["intents"]["type"] == "array"
    assert si["properties"]["intents"]["items"]["type"] == "string"
    assert set(si.get("required", [])) >= {"name", "intents"}

    # add_kb_answer: name(str, required), text(str, required), after?(str, enum)
    aa = specs["add_kb_answer"].parameters
    assert aa["properties"]["name"]["type"] == "string"
    assert aa["properties"]["text"]["type"] == "string"
    assert "after" in aa["properties"]
    assert aa["properties"]["after"]["type"] == "string"
    assert set(aa["properties"]["after"].get("enum", [])) >= {"wait", "hangup"}
    assert set(aa.get("required", [])) >= {"name", "text"}

    # edit_kb_answer: name(str, required), new_text(str, required), old_text?(str), index?(int), after?(str, enum)
    ea = specs["edit_kb_answer"].parameters
    assert ea["properties"]["name"]["type"] == "string"
    assert ea["properties"]["new_text"]["type"] == "string"
    assert "old_text" in ea["properties"]
    assert "index" in ea["properties"]
    assert "after" in ea["properties"]
    assert ea["properties"]["after"]["type"] == "string"
    assert set(ea["properties"]["after"].get("enum", [])) >= {"wait", "hangup"}
    assert set(ea.get("required", [])) >= {"name", "new_text"}

    # remove_kb_answer: name(str, required), text?(str), index?(int)
    ra = specs["remove_kb_answer"].parameters
    assert ra["properties"]["name"]["type"] == "string"
    assert "text" in ra["properties"]
    assert "index" in ra["properties"]
    assert set(ra.get("required", [])) >= {"name"}

    # set_kb_multiround: name(str, required), target_component(str/null)
    sm = specs["set_kb_multiround"].parameters
    assert sm["properties"]["name"]["type"] == "string"
    assert "target_component" in sm["properties"]
    assert set(sm.get("required", [])) >= {"name"}

    # delete_kb: name(str, required)
    dk = specs["delete_kb"].parameters
    assert dk["properties"]["name"]["type"] == "string"
    assert set(dk.get("required", [])) >= {"name"}


# ---------------------------------------------------------------------------
# Parametrized dispatch test — each tool routes to its op without error
# Each test case is independent: the fixture kb_doc is read-only (module scope).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool_name,args", [
    ("rename_kb",         {"name": "FAQ", "new_name": "FAQ-renamed"}),
    ("set_kb_intents",    {"name": "FAQ", "intents": ["Positive"]}),
    ("add_kb_answer",     {"name": "FAQ", "text": "Tentu saja bisa."}),
    ("add_kb_answer",     {"name": "FAQ", "text": "Tentu saja bisa.", "after": "hangup"}),
    ("edit_kb_answer",    {"name": "FAQ", "new_text": "Bisa bantu Anda.",
                           "old_text": "Ya, kami bisa membantu."}),
    ("edit_kb_answer",    {"name": "FAQ", "new_text": "Bisa bantu Anda.",
                           "old_text": "Ya, kami bisa membantu.", "after": "wait"}),
    ("set_kb_multiround", {"name": "FAQ", "target_component": "2. Multi"}),
    ("delete_kb",         {"name": "FAQ"}),
])
def test_kb_edit_dispatch_returns_proposal(tool_name, args, kb_doc):
    """dispatch <tool_name> builds the corresponding op and returns a proposal."""
    out = registry.dispatch(tool_name, args, kb_doc)
    assert out["result"]["ok"] is True, (
        f"{tool_name} dispatch failed: {out['result'].get('error')}"
    )
    assert out["proposal"] is not None, f"{tool_name}: proposal is None"
    assert isinstance(out["proposal"]["proposed_data"], dict), (
        f"{tool_name}: proposed_data is not a dict"
    )


# ---------------------------------------------------------------------------
# remove_kb_answer needs its own test with a 2-answer KB doc
# (engine refuses to remove the last answer)
# ---------------------------------------------------------------------------

def test_remove_kb_answer_dispatch(kb_doc):
    """remove_kb_answer dispatch on a 2-answer KB returns a proposal."""
    # First add a second answer
    added = registry.dispatch("add_kb_answer",
                              {"name": "FAQ", "text": "Jawaban kedua."}, kb_doc)
    assert added["result"]["ok"] is True, added["result"].get("error")
    doc2 = added["proposal"]["proposed_data"]

    # Now remove the first answer by text
    out = registry.dispatch("remove_kb_answer",
                            {"name": "FAQ", "text": "Ya, kami bisa membantu."}, doc2)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_set_kb_multiround_remove_dispatch(kb_doc):
    """set_kb_multiround with target_component=None exercises the remove path."""
    # First set a delegate so there is something to remove
    set_out = registry.dispatch("set_kb_multiround",
                                {"name": "FAQ", "target_component": "2. Multi"}, kb_doc)
    assert set_out["result"]["ok"] is True, set_out["result"].get("error")
    doc2 = set_out["proposal"]["proposed_data"]
    # Now remove it (null target)
    out = registry.dispatch("set_kb_multiround",
                            {"name": "FAQ", "target_component": None}, doc2)
    assert out["result"]["ok"] is True, out["result"].get("error")
    assert isinstance(out["proposal"]["proposed_data"], dict)
