"""Tests for the set-node-config op — retarget/reconfigure an existing node in place.

Fixtures mirror test_ops_kb_edit.py (builder-compiled manifest -> InputBundle,
op called directly with an IdMinter) and test_append_goto_mr.py (hand-assembled
multi-component export via run_mods) — no hand-written raw export JSON.

The combined manifest is written into tmp_path (not a checked-in fixtures file)
so it never needs to be added to git.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SK / "wiz-builder" / "scripts"))
sys.path.insert(0, str(_SK / "wiz-modifier" / "scripts"))

from wizbuilder.compile import compile_manifest  # noqa: E402
from wizbuilder.ids import IdMinter  # noqa: E402

from wizmodifier import codec  # noqa: E402
from wizmodifier.apply import run_mods  # noqa: E402
from wizmodifier.floweditor import FlowEditor  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops.mutate import set_node_config  # noqa: E402

_TEMPLATE = _SK / "wiz-builder" / "templates" / "empty_dialogue.json"

_MANIFEST_YAML = """
name: "Set Node Config Test Bot"
branch: dev
language: IDN

custom_intents:
  - name: AskPayment
    language: IDN
    keywords: ["bayar", "cicilan"]
    user_responses: ["bagaimana cara bayar"]

custom_variables:
  - name: PAYMENT_STATUS
  - name: DUE_AMOUNT

knowledge_bases:
  - name: "Payment FAQ"
    intents:
      - AskPayment
    answers:
      - "Pembayaran bisa dilakukan melalui transfer bank."
  - name: "Installment FAQ"
    intents:
      - AskPayment
    answers:
      - "Cicilan tersedia untuk 3, 6, dan 12 bulan."

canvases:
  - name: "1. Main"
    nodes:
      - id: greet
        prompt: "Greeting prompt"
      - id: gkb
        type: goto_kb
        config:
          target: "Payment FAQ"
      - id: check_status
        type: conditional
        prompt: "(conditional)"
        config:
          variable: PAYMENT_STATUS
          branches:
            - name: Paid
              op: "="
              value: "paid"
              to: assign_amt
            - name: Default
              to: greet_unpaid
      - id: assign_amt
        type: assign
        prompt: "(assign)"
        config:
          variable: DUE_AMOUNT
          value: "0"
      - id: greet_unpaid
        type: talk
        prompt: "Unpaid greeting"
      - id: done
        type: exit
        prompt: "(exit)"
    edges:
      - {from: greet, branch: Unclassified, to: gkb}
      - {from: greet, branch: Positive, to: check_status}
      - {from: assign_amt, branch: Default, to: done}
      - {from: greet_unpaid, branch: Positive, to: done}
"""


def _bundle(tmp_path) -> InputBundle:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(_MANIFEST_YAML, encoding="utf-8")
    out = tmp_path / "s.json"
    compile_manifest(manifest_path, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    return InputBundle(data=data, speech_name="s.json")


def _minter():
    return IdMinter(manifest_hash="test-set-node-config")


def _comps(b: InputBundle) -> list[dict]:
    raw = b.data["BizSpeechComponent"]
    return json.loads(raw) if isinstance(raw, str) else raw


def _uuid_of_type(comp: dict, node_type: int) -> str:
    fe = FlowEditor(comp)
    return next(u for u, n in fe.details.items() if n["type"] == node_type)


def _make_mr_export():
    """4-component export: A(cat1), B(cat2, has a goto_mr node -> C), C(cat2), D(cat2).

    Same construction as test_append_goto_mr.py, extended with a 4th (D) so the
    goto_mr node has a second valid multi-round target to retarget onto.
    """
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
    comp_d = dict(comp_a)
    comp_d["name"] = "4. D Canvas"
    comp_d["componentUuid"] = "uuid-d"
    comp_d["sortIndex"] = 4
    comp_d["details"] = "null"
    comp_d["category"] = 2
    data["BizSpeechComponent"] = json.dumps([comp_a, comp_b, comp_c, comp_d])

    b = InputBundle(data=data, speech_name="s.json")
    run_mods(
        b,
        [{"op": "append-node", "component": 1,
          "node": {"id": "jump", "type": "goto_mr", "config": {"target": "3. C Canvas"}}}],
        manifest_hash="t",
    )
    return b


# ---------------------------------------------------------------------------
# goto_kb retarget
# ---------------------------------------------------------------------------


def test_retarget_goto_kb_by_name(tmp_path):
    b = _bundle(tmp_path)
    comps = _comps(b)
    uuid = _uuid_of_type(comps[0], 8)

    kbs = codec.decode(b.data["BizKnowledgeInfo"])
    installment_id = next(k["knowledgeId"] for k in kbs if k["kdTitle"] == "Installment FAQ")

    set_node_config(b, {"component": 0, "node": {"uuid": uuid}, "kb": "Installment FAQ"}, _minter())

    comps_out = _comps(b)
    fe = FlowEditor(comps_out[0])
    assert fe.details[uuid]["data"]["appoint_knowledge_id"] == str(installment_id)


def test_unknown_kb_raises(tmp_path):
    b = _bundle(tmp_path)
    comps = _comps(b)
    uuid = _uuid_of_type(comps[0], 8)

    with pytest.raises(ValueError, match="not found in BizKnowledgeInfo"):
        set_node_config(b, {"component": 0, "node": {"uuid": uuid}, "kb": "Nonexistent KB"}, _minter())


# ---------------------------------------------------------------------------
# goto_mr retarget
# ---------------------------------------------------------------------------


def test_retarget_goto_mr_by_name():
    b = _make_mr_export()
    comps = _comps(b)
    uuid = _uuid_of_type(comps[1], 9)

    set_node_config(b, {"component": 1, "node": {"uuid": uuid}, "to_component": "4. D Canvas"}, _minter())

    comps_out = _comps(b)
    fe = FlowEditor(comps_out[1])
    d = fe.details[uuid]["data"]
    assert d["multiple_appoint_id"] == "uuid-d"
    assert d["specificComponentName"] == "4. D Canvas"
    assert not b.warnings  # D is category:2, no warning expected


def test_retarget_goto_mr_to_non_mr_component_warns():
    b = _make_mr_export()
    comps = _comps(b)
    uuid = _uuid_of_type(comps[1], 9)

    set_node_config(b, {"component": 1, "node": {"uuid": uuid}, "to_component": "1. A Canvas"}, _minter())

    comps_out = _comps(b)
    fe = FlowEditor(comps_out[1])
    d = fe.details[uuid]["data"]
    assert d["multiple_appoint_id"] == "uuid-a"
    assert any("not a multi-round" in w for w in b.warnings)


# ---------------------------------------------------------------------------
# assign edit
# ---------------------------------------------------------------------------


def test_edit_assign(tmp_path):
    b = _bundle(tmp_path)
    comps = _comps(b)
    uuid = _uuid_of_type(comps[0], 10)

    set_node_config(
        b, {"component": 0, "node": {"uuid": uuid}, "variable": "PAYMENT_STATUS", "value": "paid"}, _minter()
    )

    comps_out = _comps(b)
    fe = FlowEditor(comps_out[0])
    va = fe.details[uuid]["data"]["value_assignment"][0]
    assert va["variable"]["name"] == "PAYMENT_STATUS"
    assert va["assign"]["params"][0]["value"] == "paid"


# ---------------------------------------------------------------------------
# conditional edit
# ---------------------------------------------------------------------------


def test_edit_conditional_value(tmp_path):
    b = _bundle(tmp_path)
    comps = _comps(b)
    uuid = _uuid_of_type(comps[0], 7)

    set_node_config(
        b,
        {"component": 0, "node": {"uuid": uuid},
         "branches": [{"name": "Paid", "op": "NotIn", "value": "unpaid"}]},
        _minter(),
    )

    comps_out = _comps(b)
    fe = FlowEditor(comps_out[0])
    cond = fe.details[uuid]["data"]["branch"][0]["branch_judgement_condition"][0]
    assert cond["operator"] == "Not in"
    assert cond["right_value"] == "unpaid"


# ---------------------------------------------------------------------------
# unsupported node type
# ---------------------------------------------------------------------------


def test_unsupported_node_type_raises(tmp_path):
    b = _bundle(tmp_path)
    comps = _comps(b)
    uuid = _uuid_of_type(comps[0], 1)  # "greet" talk node

    with pytest.raises(ValueError, match="does not support node type"):
        set_node_config(b, {"component": 0, "node": {"uuid": uuid}}, _minter())
