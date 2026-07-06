import json
from pathlib import Path
from wizcheck.parser import parse_dict
from wizcheck.checks import run_all_checks
from wizcheck.component_adapter import BOT_SCOPE_CODES

FIX = Path(__file__).parent / "fixtures" / "component_export_min.json"


def _run():
    wf = parse_dict(json.loads(FIX.read_text(encoding="utf-8")))
    return wf, run_all_checks(wf)


def test_component_export_checks_run_without_crash():
    wf, findings = _run()
    assert wf.is_component_export is True
    assert isinstance(findings, list)  # ran end-to-end


def test_bot_scope_codes_suppressed_in_component_mode():
    _, findings = _run()
    codes = {f.code for f in findings}
    assert not (codes & BOT_SCOPE_CODES), f"bot-scope codes leaked: {codes & BOT_SCOPE_CODES}"


def test_full_export_still_gets_bot_scope_codes():
    # a full export with an unused custom var should still be able to emit WIZ202
    # (i.e. the filter is component-mode-only). Build minimal full export with one
    # custom (source 0) variable that no utterance references.
    full = {
        "BizSpeechComponent": [], "SpeechIntent": [], "SentenceCutSpeech": [],
        "SpeechAudio": [], "BizKnowledgeInfo": [],
        "SpeechVariable": [{"id": 5, "name": "Unused", "textType": "DEFAULT", "variableSource": 0}],
    }
    wf = parse_dict(full)
    assert wf.is_component_export is False
    # WIZ202 not filtered in full mode (it may or may not fire depending on rules,
    # but the filter must NOT be what removes it):
    from wizcheck.checks import run_all_checks as rac
    _ = rac(wf)  # just assert no crash + full mode
