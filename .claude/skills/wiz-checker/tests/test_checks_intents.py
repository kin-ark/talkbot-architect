"""Tests for checks.intents — intent coverage WIZ300..WIZ399."""

from __future__ import annotations

from wizcheck.checks.intents import check_intents
from wizcheck.ir import FlowGraph, Intent, WizFile
from wizcheck.report import Severity


def _intent(intent_id: int, name: str) -> Intent:
    return Intent(
        intent_id=intent_id, name=name, language="IDN",
        keywords=(), user_responses=(), raw={},
    )


def _wf(intents: dict) -> WizFile:
    return WizFile(
        raw={}, components={}, variables={},
        intents=intents, utterances=(), audios={}, flow=FlowGraph(),
    )


def test_wiz301_missing_negative_is_error():
    wf = _wf(intents={1: _intent(1, "Positive")})
    findings = check_intents(wf)
    f = next((x for x in findings if x.code == "WIZ301"), None)
    assert f is not None
    assert f.severity is Severity.ERROR


def test_wiz301_present_negative_does_not_fire():
    wf = _wf(intents={1: _intent(1, "Negative")})
    findings = check_intents(wf)
    assert not any(f.code == "WIZ301" for f in findings)


def test_wiz302_missing_all_fallbacks_is_error():
    wf = _wf(intents={1: _intent(1, "Negative")})  # no Unspecified/DNC/Answering Machine
    findings = check_intents(wf)
    f = next((x for x in findings if x.code == "WIZ302"), None)
    assert f is not None
    assert f.severity is Severity.ERROR


def test_wiz302_any_fallback_satisfies():
    wf = _wf(intents={1: _intent(1, "Negative"), 2: _intent(2, "DNC")})
    findings = check_intents(wf)
    assert not any(f.code == "WIZ302" for f in findings)
