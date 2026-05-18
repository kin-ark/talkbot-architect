"""Intent-coverage checks (WIZ300..WIZ399)."""

from __future__ import annotations

from pathlib import Path

import yaml

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity

_RULES_FILE = Path(__file__).resolve().parents[3] / "schema" / "intent_rules.yaml"


def _load_rules() -> dict:
    if not _RULES_FILE.exists():
        return {
            "required_intent_names": ["Negative"],
        }
    return yaml.safe_load(_RULES_FILE.read_text(encoding="utf-8")) or {}


_RULES = _load_rules()


def check_intents(wf: WizFile) -> list[Finding]:
    present_names = {i.name for i in wf.intents.values()}
    out: list[Finding] = []

    # WIZ301: required intents present
    for required in _RULES.get("required_intent_names", []):
        if required not in present_names:
            out.append(Finding(
                code="WIZ301",
                severity=Severity.ERROR,
                location=Location(entity="WizFile", id=None, field="SpeechIntent"),
                message=f"Required intent {required!r} is not declared.",
            ))

    return out
