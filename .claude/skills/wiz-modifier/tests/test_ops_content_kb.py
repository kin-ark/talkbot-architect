"""Tests for the add_kb content op."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# wiz-builder's scripts dir is a sibling skill, not on pythonpath.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "wiz-builder" / "scripts")
)

from wizbuilder.ids import IdMinter  # noqa: E402
from wizmodifier import codec  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops.content import add_kb  # noqa: E402

MINTER = IdMinter(manifest_hash="deadbeef")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bundle(baseline_dict: dict) -> InputBundle:
    """Return a fresh InputBundle from the baseline export."""
    return InputBundle(data=dict(baseline_dict), speech_name="s.json")


def _bk_list(bundle: InputBundle) -> list[dict]:
    return codec.decode(bundle.data["BizKnowledgeInfo"])


def _sck_list(bundle: InputBundle) -> list[dict]:
    return codec.decode(bundle.data["SentenceCutKnowledge"])


def _si_list(bundle: InputBundle) -> list[dict]:
    return codec.decode(bundle.data["SpeechIntent"])


# ---------------------------------------------------------------------------
# (a) Simple add_kb: entry appended, SCK rows, intent resolved
# ---------------------------------------------------------------------------


def test_add_kb_appends_entry_and_sck_rows(baseline_dict):
    b = _make_bundle(baseline_dict)
    bk_before = len(_bk_list(b))
    sck_before = len(_sck_list(b))

    # "Can not hear clearly" is the first intent in Empty+Dialogue.
    add_kb(
        b,
        {
            "name": "Test KB",
            "intents": ["Can not hear clearly"],
            "answers": ["Answer one", "Answer two"],
        },
        MINTER,
    )

    bk = _bk_list(b)
    sck = _sck_list(b)
    assert len(bk) == bk_before + 1
    assert len(sck) == sck_before + 2  # 2 answers → 2 SCK rows

    entry = bk[-1]
    assert entry["kdTitle"] == "Test KB"
    assert entry["answerType"] == 1
    assert entry["isInit"] == 0
    assert entry["recordNum"] == 0
    assert entry["wordNum"] == 0


def test_add_kb_intents_resolved_in_entry(baseline_dict):
    b = _make_bundle(baseline_dict)
    si = _si_list(b)
    intent = next(i for i in si if i["intentName"] == "Can not hear clearly")

    add_kb(
        b,
        {
            "name": "Intent KB",
            "intents": ["Can not hear clearly"],
            "answers": ["Hello"],
        },
        MINTER,
    )

    entry = _bk_list(b)[-1]
    resolved = json.loads(entry["intents"])
    assert len(resolved) == 1
    assert resolved[0]["intentName"] == "Can not hear clearly"
    assert resolved[0]["intentId"] == intent["intentId"]


def test_add_kb_sck_rows_shape(baseline_dict):
    b = _make_bundle(baseline_dict)
    sck_before = len(_sck_list(b))

    add_kb(
        b,
        {"name": "Shape KB", "intents": ["Can not hear clearly"], "answers": ["Hello"]},
        MINTER,
    )

    new_rows = _sck_list(b)[sck_before:]
    assert len(new_rows) == 1
    row = new_rows[0]
    expected_keys = {
        "branch", "id", "isDelete", "knowledgeId", "knowledgeRecCutId",
        "senRecName", "sentenceText", "sentenceTextUrl", "showType",
        "speechId", "speechRecCutId", "type",
    }
    assert set(row.keys()) == expected_keys
    assert row["sentenceText"] == "Hello"
    assert row["type"] == "record"
    # speechRecCutId must be a UUID-format string (not a wide-int)
    import re
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    assert re.match(uuid_pattern, row["speechRecCutId"])
    # knowledgeRecCutId must be an int
    assert isinstance(row["knowledgeRecCutId"], int)


def test_add_kb_no_sck_rows_for_zero_answers(baseline_dict):
    b = _make_bundle(baseline_dict)
    sck_before = len(_sck_list(b))

    add_kb(
        b,
        {"name": "Empty KB", "intents": ["Can not hear clearly"], "answers": []},
        MINTER,
    )

    assert len(_sck_list(b)) == sck_before  # no new SCK rows


# ---------------------------------------------------------------------------
# (b) multi_round: delegate item appended, componentUuid resolved
# ---------------------------------------------------------------------------


def test_add_kb_multi_round_appends_delegate_item(baseline_dict):
    b = _make_bundle(baseline_dict)
    # The baseline has one component "Dialogue Open"
    bsc = codec.decode(b.data["BizSpeechComponent"])
    comp_name = bsc[0]["name"]
    comp_uuid = bsc[0]["componentUuid"]
    sck_before = len(_sck_list(b))

    add_kb(
        b,
        {
            "name": "Multi KB",
            "intents": ["Can not hear clearly"],
            "answers": ["Main answer"],
            "multi_round": comp_name,
        },
        MINTER,
    )

    entry = _bk_list(b)[-1]
    kd_info = json.loads(entry["kdInfo"])

    # 1 answer item + 1 delegate item
    assert len(kd_info) == 2
    normal_item = kd_info[0]
    delegate_item = kd_info[1]

    assert normal_item["answerType"] == 1
    assert normal_item["answer"] == "Main answer"

    assert delegate_item["answerType"] == 2
    assert delegate_item["multipleAppointId"] == comp_uuid
    assert delegate_item["editorValue"]["text"] == ""
    assert delegate_item["editorValue"]["html"] == "<p></p>"
    assert "<speak" in delegate_item["editorValue"]["xml"]

    # SCK rows: only the normal answerType:1 answer gets one
    assert len(_sck_list(b)) == sck_before + 1

    # The multi_round target component must be re-classified category=2 so WIZ files it
    # under the Multi-Round Dialogue tab (decoded from real export).
    bsc_after = {c["componentUuid"]: c for c in codec.decode(b.data["BizSpeechComponent"])}
    assert bsc_after[comp_uuid]["category"] == 2, (
        f"multi_round target must become category 2; got {bsc_after[comp_uuid].get('category')}"
    )


def test_add_kb_multi_round_no_answers_only_delegate(baseline_dict):
    b = _make_bundle(baseline_dict)
    bsc = codec.decode(b.data["BizSpeechComponent"])
    comp_name = bsc[0]["name"]

    add_kb(
        b,
        {
            "name": "Delegate Only KB",
            "intents": ["Can not hear clearly"],
            "answers": [],
            "multi_round": comp_name,
        },
        MINTER,
    )

    entry = _bk_list(b)[-1]
    kd_info = json.loads(entry["kdInfo"])
    assert len(kd_info) == 1
    assert kd_info[0]["answerType"] == 2


# ---------------------------------------------------------------------------
# (c) undeclared intent raises ValueError
# ---------------------------------------------------------------------------


def test_add_kb_undeclared_intent_raises(baseline_dict):
    b = _make_bundle(baseline_dict)
    with pytest.raises(ValueError, match="intent.*NoSuchIntent|NoSuchIntent.*intent"):
        add_kb(
            b,
            {"name": "Bad KB", "intents": ["NoSuchIntent"], "answers": ["Hi"]},
            MINTER,
        )


# ---------------------------------------------------------------------------
# (d) duplicate kdTitle raises ValueError
# ---------------------------------------------------------------------------


def test_add_kb_duplicate_title_raises(baseline_dict):
    b = _make_bundle(baseline_dict)
    # "Can not hear clearly" is an existing KB title in Empty+Dialogue
    with pytest.raises(ValueError, match="already exists"):
        add_kb(
            b,
            {
                "name": "Can not hear clearly",
                "intents": ["Can not hear clearly"],
                "answers": ["Hi"],
            },
            MINTER,
        )


def test_add_kb_duplicate_after_first_add_raises(baseline_dict):
    b = _make_bundle(baseline_dict)
    add_kb(
        b,
        {"name": "New KB", "intents": ["Can not hear clearly"], "answers": ["Hello"]},
        MINTER,
    )
    with pytest.raises(ValueError, match="already exists"):
        add_kb(
            b,
            {"name": "New KB", "intents": ["Can not hear clearly"], "answers": ["Hi"]},
            MINTER,
        )


# ---------------------------------------------------------------------------
# (e) unknown multi_round component raises ValueError
# ---------------------------------------------------------------------------


def test_add_kb_unknown_multi_round_raises(baseline_dict):
    b = _make_bundle(baseline_dict)
    with pytest.raises(ValueError, match="multi_round.*NoSuchComp|NoSuchComp.*multi_round"):
        add_kb(
            b,
            {
                "name": "MR KB",
                "intents": ["Can not hear clearly"],
                "answers": ["Hi"],
                "multi_round": "NoSuchComp",
            },
            MINTER,
        )
