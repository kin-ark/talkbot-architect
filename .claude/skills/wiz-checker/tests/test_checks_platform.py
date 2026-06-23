"""Tests for checks.platform — manual-documented constraints WIZ400..WIZ499."""
from __future__ import annotations

from wizcheck.checks.platform import check_platform
from wizcheck.ir import Intent, WizFile
from wizcheck.report import Severity


def _wf(intents: dict | None = None) -> WizFile:
    return WizFile(
        raw={}, components={}, variables={},
        intents=intents or {}, utterances=(), audios={}, knowledge_bases={},
    )


def _intent(intent_id: int, language: str) -> Intent:
    return Intent(
        intent_id=intent_id, name="X", language=language,
        keywords=(), user_responses=(), raw={},
    )


def test_wiz400_unsupported_language_is_error():
    wf = _wf(intents={1: _intent(1, "JPN")})
    findings = check_platform(wf)
    f = next((x for x in findings if x.code == "WIZ400"), None)
    assert f is not None
    assert f.severity is Severity.ERROR
    assert "JPN" in f.message


def test_wiz400_supported_language_does_not_fire():
    wf = _wf(intents={1: _intent(1, "IDN"), 2: _intent(2, "THA")})
    findings = check_platform(wf)
    assert not any(f.code == "WIZ400" for f in findings)


def test_wiz400_skips_empty_or_zero_language():
    wf = _wf(intents={1: _intent(1, "")})
    findings = check_platform(wf)
    assert not any(f.code == "WIZ400" for f in findings)
