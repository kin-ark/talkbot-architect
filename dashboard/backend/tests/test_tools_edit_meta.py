"""Tests for add_intent + add_variable tool wiring (Task 4 / E-T4)."""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from tools import registry  # noqa: E402

# Minimal DATA with enough shape for add-intent and add-variable ops to succeed.
# - SpeechIntent must be non-empty (op raises if empty)
# - SpeechVariable must be non-empty (op raises if empty)
# Both are passed as Python lists; agents._ensure_packed re-encodes them as JSON strings.
_INTENT_DEFAULTS = [{"branch": "dev", "createTime": 0, "intentId": 1, "intentName": "Positive",
                      "isDelete": 0, "isInit": 0, "keyWordInIntent": "[]", "language": "ENG",
                      "nodeId": "", "speechId": 1, "templateCode": "tpl", "updateTime": 0,
                      "userResponseInIntent": "[]"}]
_VAR_DEFAULTS = [{"beInit": 0, "branch": "dev", "createTime": 0, "enumVariable": 0,
                  "id": 100, "name": "DEFAULT", "speechId": 1, "templateCode": "tpl",
                  "textType": "", "type": 1, "userId": 9, "variableSource": 0}]

DATA = {
    "BizSpeechComponent": [{"componentUuid": "00000000-0000-0000-0000-000000000001",
                             "name": "Main", "speechId": 1, "details": "null"}],
    "SpeechIntent": _INTENT_DEFAULTS,
    "SpeechVariable": _VAR_DEFAULTS,
    "BizKnowledgeInfo": [],
}


def test_intent_variable_tools_registered():
    names = [s.name for s in registry.tool_specs()]
    assert "add_intent" in names
    assert "add_variable" in names


def test_add_variable_returns_proposal():
    out = registry.dispatch("add_variable", {"name": "DEBT_AMOUNT"}, DATA)
    assert out["result"]["ok"] is True
    assert out["proposal"] is not None


def test_add_intent_returns_proposal():
    out = registry.dispatch("add_intent", {"name": "WANTS_PAYMENT", "language": "ENG"}, DATA)
    assert out["result"]["ok"] is True
    assert out["proposal"] is not None


def test_add_intent_with_keywords():
    out = registry.dispatch(
        "add_intent",
        {"name": "OPT_OUT", "language": "ENG", "keywords": ["stop", "cancel"]},
        DATA,
    )
    assert out["result"]["ok"] is True
    assert out["proposal"] is not None


def test_add_intent_bad_language_errors():
    """Unsupported language code → op fails (ValueError → ok=False)."""
    out = registry.dispatch("add_intent", {"name": "TEST", "language": "ZZZ"}, DATA)
    assert out["result"]["ok"] is False
