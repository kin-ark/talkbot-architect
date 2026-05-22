"""End-to-end integration tests for wiz-builder: build + wiz-checker validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from wizbuilder.compile import compile_manifest

SKILL_DIR = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_DIR / "tests" / "fixtures"
GOLDEN_DIR = SKILL_DIR / "tests" / "golden"
PROJECT_ROOT = SKILL_DIR.parents[2]
CHECKER_CLI = PROJECT_ROOT / ".claude" / "skills" / "wiz-checker" / "scripts" / "check.py"


@pytest.mark.parametrize("manifest_name", [
    "manifest_minimal.yaml",
    "manifest_multi_canvas.yaml",
    "manifest_with_customs.yaml",
])
def test_build_produces_checker_clean_output(manifest_name, tmp_path):
    out = tmp_path / "speech.json"
    result = compile_manifest(FIXTURES / manifest_name, out)
    assert result.checker_errors == 0, f"Errors: {result.finding_codes}"


def test_multi_canvas_golden_matches(tmp_path):
    """The multi-canvas build output is bit-stable across re-compilations."""
    out = tmp_path / "speech.json"
    compile_manifest(FIXTURES / "manifest_multi_canvas.yaml", out)
    actual = json.loads(out.read_text(encoding="utf-8"))

    # Normalize the speechId (it's random per build).
    actual = _normalize(actual)

    golden_path = GOLDEN_DIR / "multi_canvas.expected.json"
    if not golden_path.exists():
        pytest.skip(f"Golden not present: {golden_path}")
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    if actual != expected:
        pytest.fail(
            "Golden mismatch. To update:\n"
            f"  python -c \"import json,sys; from tests.test_integration import _normalize; "
            f"d=_normalize(json.load(open(r'{out}', encoding='utf-8'))); "
            f"open(r'{golden_path}','w',encoding='utf-8').write(json.dumps(d,indent=2,ensure_ascii=False))\""
        )


def _normalize(data: dict) -> dict:
    """Zero out the random speechId so goldens are stable."""
    data = dict(data)
    for key in ("BizSpeechComponent", "SpeechVariable", "SpeechIntent", "SentenceCutSpeech", "SpeechAudio"):  # noqa: E501
        raw = data.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        items = json.loads(raw)
        for item in items:
            if "speechId" in item:
                item["speechId"] = 0
        data[key] = json.dumps(items, ensure_ascii=False)
    return data


def test_checker_finds_no_errors_on_compiled_output(tmp_path):
    """Sanity: directly invoke wiz-checker on the built file."""
    out = tmp_path / "speech.json"
    compile_manifest(FIXTURES / "manifest_with_customs.yaml", out)

    proc = subprocess.run(
        [sys.executable, str(CHECKER_CLI), str(out), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert proc.returncode in (0, 1), f"checker stderr: {proc.stderr}"
    report = json.loads(proc.stdout)
    assert report["summary"]["errors"] == 0, f"findings: {report['findings'][:3]}"
