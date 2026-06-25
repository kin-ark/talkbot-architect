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
            "required_intent_names": ["Unclassified"],
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

    # WIZ302: KB triggering intents declared in SpeechIntent
    for kb in wf.knowledge_bases.values():
        for iid in kb.intents:
            if iid not in wf.intents:
                out.append(Finding(
                    code="WIZ302",
                    severity=Severity.ERROR,
                    location=Location(
                        entity="BizKnowledgeInfo",
                        id=str(kb.knowledge_id),
                        field="intents",
                    ),
                    message=(
                        f"Knowledge base {kb.title!r} (id {kb.knowledge_id}) references"
                        f" intent id {iid} which is not declared in SpeechIntent."
                    ),
                ))

    return out
