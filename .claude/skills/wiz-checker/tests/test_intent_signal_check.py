"""Tests for WIZ305: user-intent no-signal check."""

from __future__ import annotations

import json

from wizcheck.checks.intents import check_intents
from wizcheck.parser import parse_dict
from wizcheck.report import DEPLOY_BLOCKER_CODES, Severity


def _make_export(**overrides) -> dict:
    """Create a minimal export dict with default SpeechIntent."""
    base = {
        "BizSpeechComponent": [],
        "BizKnowledgeInfo": [],
        "SpeechVariable": [],
        "SpeechIntent": [
            {
                "intentId": 1,
                "intentName": "Unclassified",
                "isInit": 0,
                "isDelete": 0,
                "language": "IDN",
                "keyWordInIntent": "[]",
                "userResponseInIntent": "[]",
                "branch": "dev",
                "speechId": 1,
                "templateCode": "DEFAULT",
                "nodeId": "",
                "createTime": 0,
                "updateTime": 0,
            }
        ],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }
    base.update(overrides)
    return base


def test_wiz305_no_signal_user_intent_warns():
    """A user-created intent (isInit=1) with no keywords and no responses -> WIZ305 WARNING."""
    doc = _make_export()
    si = json.loads(doc["SpeechIntent"]) if isinstance(doc["SpeechIntent"], str) else doc["SpeechIntent"]
    si.append({
        "intentId": 999001,
        "intentName": "Bare",
        "isInit": 1,
        "isDelete": 0,
        "language": "IDN",
        "keyWordInIntent": "[]",
        "userResponseInIntent": "[]",
        "branch": "dev",
        "speechId": si[0]["speechId"],
        "templateCode": si[0]["templateCode"],
        "nodeId": "",
        "createTime": 0,
        "updateTime": 0,
    })
    doc["SpeechIntent"] = json.dumps(si)

    wf = parse_dict(doc)
    f = [x for x in check_intents(wf) if x.code == "WIZ305"]
    assert f, "Expected WIZ305 finding for user-created intent with no signal"
    assert all(x.severity is Severity.WARNING for x in f)
    assert any("Bare" in x.message for x in f)


def test_wiz305_exempts_system_intent():
    """A system intent (isInit=0) with no keywords and no responses -> no WIZ305."""
    doc = _make_export()
    si = json.loads(doc["SpeechIntent"]) if isinstance(doc["SpeechIntent"], str) else doc["SpeechIntent"]
    si.append({
        "intentId": 999002,
        "intentName": "SysBare",
        "isInit": 0,
        "isDelete": 0,
        "language": "IDN",
        "keyWordInIntent": "[]",
        "userResponseInIntent": "[]",
        "branch": "dev",
        "speechId": si[0]["speechId"],
        "templateCode": si[0]["templateCode"],
        "nodeId": "",
        "createTime": 0,
        "updateTime": 0,
    })
    doc["SpeechIntent"] = json.dumps(si)

    wf = parse_dict(doc)
    assert not any(
        x.code == "WIZ305" and "SysBare" in x.message
        for x in check_intents(wf)
    ), "System intents should be exempt from WIZ305"


def test_wiz305_is_deploy_blocker():
    """WIZ305 is in DEPLOY_BLOCKER_CODES."""
    assert "WIZ305" in DEPLOY_BLOCKER_CODES
