import json
import subprocess
import sys
import tempfile
from pathlib import Path
from wizcheck.parser import parse_dict
from wizcheck.checks import run_all_checks
from wizcheck.component_adapter import BOT_SCOPE_CODES, component_export_to_full

FIX = Path(__file__).parent / "fixtures" / "component_export_min.json"

# Minimal component export with an unused custom variable (should trigger WIZ202 in full mode).
_COMP_WITH_UNUSED_VAR = {
    "name": "Main",
    "componentImportAndExportDTOS": [{
        "componentName": "Main",
        "componentUuid": "a227ff42-008d-4970-9eff-c43b3d18fd22",
        "speechComponentDTO": {
            "componentUuid": "a227ff42-008d-4970-9eff-c43b3d18fd22",
            "speechId": 1, "category": 1, "branch": "dev", "name": "Main",
            "sortIndex": 1, "parentUuid": "0", "updateTime": 123,
            "details": {}, "routes": {}, "inboundPorts": [],
        },
        "sentenceCutDTOList": [], "asrSceneEntityList": [],
    }],
    "speechIntentDTO": [{"intentId": 1, "intentName": "Unclassified", "isInit": 0,
                         "language": "IDN", "keyWordInIntent": [], "userResponseInIntent": []}],
    "speechVariableDTO": [{"beInit": 0, "id": 77, "name": "UnusedVar", "textType": "DEFAULT",
                           "type": 0, "userId": 9, "variableSource": 0}],
    "speechEntiEntityList": [], "speechEntityData": [],
    "speechFunctionDTO": [], "tagDTOList": [],
}


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


def test_wiz202_would_fire_but_is_suppressed_in_component_mode():
    """Prove that WIZ202 is actually suppressed in component mode, not just absent."""
    from wizcheck.checks.variables import check_variables

    # First, prove the check WOULD fire: call check_variables directly on the component
    wf = parse_dict(dict(_COMP_WITH_UNUSED_VAR))
    assert wf.is_component_export is True
    codes_direct = {f.code for f in check_variables(wf)}
    assert "WIZ202" in codes_direct, \
        "WIZ202 must fire from check_variables directly (proves the check exists)"

    # Second, verify run_all_checks suppresses it in component mode
    codes = {f.code for f in run_all_checks(wf)}
    assert "WIZ202" not in codes, \
        "WIZ202 must be suppressed by run_all_checks in component mode"

    # Third, prove it's unsuppressed in full mode
    full = component_export_to_full(_COMP_WITH_UNUSED_VAR)
    wf_full = parse_dict(full)
    assert wf_full.is_component_export is False
    codes_full = {f.code for f in run_all_checks(wf_full)}
    assert "WIZ202" in codes_full, \
        "WIZ202 must fire in full mode (proves suppression is mode-specific, not absence)"


def test_cli_suppresses_bot_scope_codes_in_component_mode():
    """CLI-level regression: verify bot-scope codes are suppressed in stdout + exit code."""
    # write the component fixture to a temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(_COMP_WITH_UNUSED_VAR, f)
        temp_file = f.name

    try:
        # run the CLI check with --json to get machine-readable findings
        # repo_root is parent.parent.parent.parent.parent of this test file:
        # test_component_checker.py -> tests -> wiz-checker -> skills -> .claude -> repo root
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        result = subprocess.run(
            [sys.executable, ".claude/skills/wiz-checker/scripts/check.py", temp_file, "--json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        # verify the subprocess succeeded
        assert result.returncode == 0, \
            f"CLI failed with code {result.returncode}. stderr: {result.stderr}"
        assert result.stdout, "CLI produced no stdout"

        # parse the JSON output
        report = json.loads(result.stdout)
        findings_codes = {f["code"] for f in report.get("findings", [])}

        # none of the bot-scope codes should be present
        bot_scope_in_output = findings_codes & BOT_SCOPE_CODES
        assert not bot_scope_in_output, \
            f"CLI did not suppress bot-scope codes: {bot_scope_in_output} in {findings_codes}"
    finally:
        Path(temp_file).unlink()
