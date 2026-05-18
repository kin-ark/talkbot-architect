"""Tests for the CLI entry point (scripts/check.py)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
CLI = SKILL_DIR / "scripts" / "check.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        cwd=SKILL_DIR,
        encoding="utf-8",
    )


def test_cli_clean_minimal_exits_zero():
    # minimal_valid.json declares Negative and Unclassified intents (intent-coverage
    # satisfied). Name is a platform-default variable, so no WIZ202 fires. Exit 0.
    fixture = SKILL_DIR / "tests" / "fixtures" / "minimal_valid.json"
    result = _run(str(fixture), "--json")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["file"].endswith("minimal_valid.json")


def test_cli_json_output_is_parseable():
    fixture = SKILL_DIR / "tests" / "fixtures" / "minimal_valid.json"
    result = _run(str(fixture), "--json")
    parsed = json.loads(result.stdout)
    assert "summary" in parsed
    assert "findings" in parsed
    assert isinstance(parsed["findings"], list)


def test_cli_parse_error_exits_three(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid", encoding="utf-8")
    result = _run(str(bad))
    assert result.returncode == 3


def test_cli_missing_file_exits_three(tmp_path):
    result = _run(str(tmp_path / "nonexistent.json"))
    assert result.returncode == 3


def test_cli_only_filter_runs_subset():
    fixture = SKILL_DIR / "tests" / "fixtures" / "minimal_valid.json"
    result = _run(str(fixture), "--only", "WIZ2", "--json")
    parsed = json.loads(result.stdout)
    # Only WIZ2** findings should appear
    for f in parsed["findings"]:
        assert f["code"].startswith("WIZ2")


def test_cli_strict_promotes_warnings_to_failures(tmp_path):
    # Build a file that produces only WIZ202 warnings (declared but unused var)
    # Use a non-platform-default name so WIZ202 still fires
    payload = {
        "BizSpeechComponent": [],
        "SpeechVariable": [
            {"id": 1, "name": "CustomerLoyaltyTier", "textType": "DEFAULT", "type": 0},
        ],
        "SpeechIntent": [
            {"intentId": 1, "intentName": "Negative", "language": "IDN",
             "keyWordInIntent": [], "userResponseInIntent": []},
            {"intentId": 2, "intentName": "Unclassified", "language": "IDN",
             "keyWordInIntent": [], "userResponseInIntent": []},
        ],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }
    p = tmp_path / "warn_only.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    # Without --strict: exit 0 (warnings allowed)
    r1 = _run(str(p))
    assert r1.returncode == 0
    # With --strict: exit 1 (warnings promoted to errors)
    r2 = _run(str(p), "--strict")
    assert r2.returncode == 1
