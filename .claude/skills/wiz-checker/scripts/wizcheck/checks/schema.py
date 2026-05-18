"""Schema-shape checks (WIZ001..WIZ099).

Rules are loaded from schema/schema_rules.yaml at module-import time so they
can be tweaked without code changes during schema discovery.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity

_RULES_FILE = Path(__file__).resolve().parents[3] / "schema" / "schema_rules.yaml"


def _load_rules() -> dict:
    if not _RULES_FILE.exists():
        return {
            "required_top_level_keys": [
                "BizSpeechComponent", "SpeechVariable", "SpeechIntent",
                "SentenceCutSpeech", "SpeechAudio",
            ],
            "known_component_categories": [1],
            "known_branches": ["dev", "prod"],
            "known_intent_languages": ["IDN", "ENG", "ZHO"],
        }
    return yaml.safe_load(_RULES_FILE.read_text(encoding="utf-8")) or {}


_RULES = _load_rules()


def check_schema(wf: WizFile) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_required_top_level(wf))
    findings.extend(_check_component_categories(wf))
    findings.extend(_check_component_branches(wf))
    findings.extend(_check_intent_languages(wf))
    findings.extend(_check_component_timestamps(wf))
    return findings


def _check_required_top_level(wf: WizFile) -> list[Finding]:
    required = _RULES.get("required_top_level_keys", [])
    out: list[Finding] = []
    for key in required:
        if key not in wf.raw:
            out.append(Finding(
                code="WIZ001",
                severity=Severity.ERROR,
                location=Location(entity="WizFile", id=None, field=key),
                message=f"Required top-level key '{key}' is missing from the export.",
            ))
    return out


def _check_component_categories(wf: WizFile) -> list[Finding]:
    known = set(_RULES.get("known_component_categories", []))
    out: list[Finding] = []
    for comp in wf.components.values():
        if comp.category not in known:
            out.append(Finding(
                code="WIZ002",
                severity=Severity.WARNING,
                location=Location(entity="Component", id=str(comp.uuid), field="category"),
                message=f"Unknown component category {comp.category!r} (known: {sorted(known)}).",
            ))
    return out


def _check_component_branches(wf: WizFile) -> list[Finding]:
    known = set(_RULES.get("known_branches", []))
    out: list[Finding] = []
    for comp in wf.components.values():
        if comp.branch not in known:
            out.append(Finding(
                code="WIZ003",
                severity=Severity.WARNING,
                location=Location(entity="Component", id=str(comp.uuid), field="branch"),
                message=f"Unknown branch {comp.branch!r} (known: {sorted(known)}).",
            ))
    return out


def _check_intent_languages(wf: WizFile) -> list[Finding]:
    known = set(_RULES.get("known_intent_languages", []))
    out: list[Finding] = []
    for intent in wf.intents.values():
        if not intent.language:  # "" or None: language unset, not unknown
            continue
        if intent.language not in known:
            out.append(Finding(
                code="WIZ004",
                severity=Severity.WARNING,
                location=Location(entity="Intent", id=str(intent.intent_id), field="language"),
                message=f"Unknown intent language {intent.language!r} (known: {sorted(known)}).",
            ))
    return out


def _check_component_timestamps(wf: WizFile) -> list[Finding]:
    out: list[Finding] = []
    for comp in wf.components.values():
        ct = comp.raw.get("createTime", 0)
        ut = comp.raw.get("updateTime", 0)
        if not ct and not ut:
            out.append(Finding(
                code="WIZ005",
                severity=Severity.ERROR,
                location=Location(entity="Component", id=str(comp.uuid), field="createTime"),
                message="Component has zero/missing createTime and updateTime; likely export bug.",
            ))
    return out
