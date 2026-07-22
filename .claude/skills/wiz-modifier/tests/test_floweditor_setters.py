"""Tests for FlowEditor config setters — goto_kb/goto_mr/assign/conditional retarget.

Mirrors the fixture-building conventions in test_floweditor.py (builder-compiled
manifest -> BizSpeechComponent[0]) and test_append_goto_mr.py (hand-assembled
mini export + append-node op) rather than hand-writing raw export JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# wiz-builder's scripts dir is a sibling skill, not on pythonpath.
_SKILL_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SKILL_DIR / "wiz-builder" / "scripts"))

from wizbuilder.compile import compile_manifest  # noqa: E402

from wizmodifier.apply import run_mods  # noqa: E402
from wizmodifier.floweditor import FlowEditError, FlowEditor  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402

FIX = _SKILL_DIR / "wiz-builder" / "tests" / "fixtures"
_TEMPLATE = _SKILL_DIR / "wiz-builder" / "templates" / "empty_dialogue.json"


def _uw(v):
    return json.loads(v) if isinstance(v, str) else v


def _build_comp0(tmp_path, manifest_name):
    out = tmp_path / "speech.json"
    compile_manifest(FIX / manifest_name, out)
    doc = json.loads(out.read_text(encoding="utf-8"))
    return _uw(doc["BizSpeechComponent"])[0]


@pytest.fixture
def conditional_component(tmp_path):
    """comp[0] of manifest_conditional_assign.yaml — has a conditional node
    "check_status" with branches [Paid, Default]."""
    return _build_comp0(tmp_path, "manifest_conditional_assign.yaml")


@pytest.fixture
def assign_component(tmp_path):
    """Same fixture — also has an assign node "assign_amt" (variable DUE_AMOUNT)."""
    return _build_comp0(tmp_path, "manifest_conditional_assign.yaml")


@pytest.fixture
def goto_kb_component(tmp_path):
    """comp[0] of manifest_goto_kb.yaml — has a goto_kb node targeting "Payment FAQ"."""
    return _build_comp0(tmp_path, "manifest_goto_kb.yaml")


@pytest.fixture
def goto_mr_component():
    """A category:2 component containing a goto_mr node, built the same way
    test_append_goto_mr.py does: a hand-assembled 3-component mini export
    (A: category 1, B/C: category 2) + append-node op, targeting C from B."""
    data = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
    comps = json.loads(data["BizSpeechComponent"])
    comp_a = comps[0]
    comp_a["name"] = "1. A Canvas"
    comp_a["componentUuid"] = "uuid-a"
    comp_a["category"] = 1
    comp_b = dict(comp_a)
    comp_b["name"] = "2. B Canvas"
    comp_b["componentUuid"] = "uuid-b"
    comp_b["sortIndex"] = 2
    comp_b["details"] = "null"
    comp_b["category"] = 2
    comp_c = dict(comp_a)
    comp_c["name"] = "3. C Canvas"
    comp_c["componentUuid"] = "uuid-c"
    comp_c["sortIndex"] = 3
    comp_c["details"] = "null"
    comp_c["category"] = 2
    data["BizSpeechComponent"] = json.dumps([comp_a, comp_b, comp_c])

    b = InputBundle(data=data, speech_name="s.json")
    run_mods(
        b,
        [{"op": "append-node", "component": 1,
          "node": {"id": "jump", "type": "goto_mr", "config": {"target": "3. C Canvas"}}}],
        manifest_hash="t",
    )
    comps_out = _uw(b.data["BizSpeechComponent"])
    return comps_out[1]


# ---------------------------------------------------------------------------
# goto_kb
# ---------------------------------------------------------------------------


def test_set_goto_kb_target_sets_string_id_and_tfd(goto_kb_component):
    fe = FlowEditor(goto_kb_component)
    uuid = next(u for u, n in fe.details.items() if n["type"] == 8)
    fe.set_goto_kb_target(uuid, 183805)
    assert fe.details[uuid]["data"]["appoint_knowledge_id"] == "183805"
    assert any(
        r.get("id") == uuid and r.get("appoint_knowledge_id") == "183805" for r in fe.tfd
    )


# ---------------------------------------------------------------------------
# goto_mr
# ---------------------------------------------------------------------------


def test_set_goto_mr_target(goto_mr_component):
    fe = FlowEditor(goto_mr_component)
    uuid = next(u for u, n in fe.details.items() if n["type"] == 9)
    fe.set_goto_mr_target(uuid, "COMPUUID-9", "MR Target")
    d = fe.details[uuid]["data"]
    assert d["multiple_appoint_id"] == "COMPUUID-9" and d["specificComponentName"] == "MR Target"


# ---------------------------------------------------------------------------
# assign
# ---------------------------------------------------------------------------


def test_set_assign(assign_component):
    fe = FlowEditor(assign_component)
    uuid = next(u for u, n in fe.details.items() if n["type"] == 10)
    fe.set_assign(uuid, variable="Gender", value="M", src=1)
    va = fe.details[uuid]["data"]["value_assignment"][0]
    assert va["variable"]["name"] == "Gender"
    assert va["assign"]["params"][0]["value"] == "M"
    assert fe.details[uuid]["data"]["node_variables"][0] == {"name": "Gender", "variableSource": 1}


# ---------------------------------------------------------------------------
# conditional
# ---------------------------------------------------------------------------


def test_set_conditional_updates_rule_and_keeps_ports(conditional_component):
    fe = FlowEditor(conditional_component)
    uuid = next(u for u, n in fe.details.items() if n["type"] == 7)
    before_ports = list(fe.details[uuid]["data"]["branchList"])
    fe.set_conditional(uuid, branch_updates=[{"name": "Paid", "op": "NotIn", "value": "x"}])
    cond = fe.details[uuid]["data"]["branch"][0]["branch_judgement_condition"][0]
    assert cond["operator"] == "Not in"  # canonicalized
    assert cond["right_value"] == "x"
    assert fe.details[uuid]["data"]["branchList"] == before_ports  # ports unchanged


def test_set_conditional_rejects_unknown_branch(conditional_component):
    fe = FlowEditor(conditional_component)
    uuid = next(u for u, n in fe.details.items() if n["type"] == 7)
    with pytest.raises(FlowEditError):
        fe.set_conditional(uuid, branch_updates=[{"name": "DoesNotExist", "op": "=", "value": "1"}])
