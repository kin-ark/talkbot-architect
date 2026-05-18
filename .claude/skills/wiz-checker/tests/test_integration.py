"""End-to-end integration tests against the real WIZ.AI sample files.

Goldens live in tests/golden/. Update them deliberately when checks change.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SKILL_DIR.parents[2]  # .claude/skills/wiz-checker -> project root
CLI = SKILL_DIR / "scripts" / "check.py"
GOLDEN_DIR = SKILL_DIR / "tests" / "golden"

SAMPLES = [
    PROJECT_ROOT / "talkbot" / "Test+Kinan" / "speech13139256226648334285.json",
    PROJECT_ROOT / "talkbot" / "Tiktok+Paylater+DPD0" / "speech4892384019254584542.json",
    PROJECT_ROOT / "talkbot" / "TSP+Matchmaking" / "speech2572824560161596380.json",
]


def _normalize(report: dict) -> dict:
    """Replace absolute file path with basename for stable comparison."""
    report = dict(report)
    report["file"] = Path(report["file"]).name
    return report


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda p: p.name)
def test_golden_report_matches(sample):
    if not sample.exists():
        pytest.skip(f"Sample not present: {sample}")
    golden_path = GOLDEN_DIR / f"{sample.stem}.expected.json"
    if not golden_path.exists():
        pytest.skip(f"Golden not present: {golden_path}")

    result = subprocess.run(
        [sys.executable, str(CLI), str(sample), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode in (0, 1), (
        f"CLI exited {result.returncode} unexpectedly; stderr:\n{result.stderr}"
    )
    actual = _normalize(json.loads(result.stdout))
    expected = json.loads(golden_path.read_text(encoding="utf-8"))

    if actual != expected:
        actual_str = json.dumps(actual, indent=2, sort_keys=True)
        expected_str = json.dumps(expected, indent=2, sort_keys=True)
        pytest.fail(
            f"Golden mismatch for {sample.name}.\n"
            f"To update: python scripts/check.py {sample} --json > "
            f"tests/golden/{sample.stem}.expected.json (then normalize 'file' field)\n"
            f"--- expected ---\n{expected_str}\n"
            f"--- actual ---\n{actual_str}"
        )
