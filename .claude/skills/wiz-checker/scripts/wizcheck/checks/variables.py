"""Variable consistency checks (WIZ200..WIZ299)."""

from __future__ import annotations

from pathlib import Path

import yaml

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity

_RULES_FILE = Path(__file__).resolve().parents[3] / "schema" / "variable_rules.yaml"

_PLATFORM_DEFAULT_FALLBACK = [
    "Phone",
    "Gender",
    "Email",
    "Answering Machine",
    "Greeting",
    "Today",
    "Call Time",
    "Follow-up Stage",
    "Customer Segment",
    "Name",
]


def _load_rules() -> dict:
    if not _RULES_FILE.exists():
        return {"platform_default_variables": _PLATFORM_DEFAULT_FALLBACK}
    return yaml.safe_load(_RULES_FILE.read_text(encoding="utf-8")) or {}


_RULES = _load_rules()
_PLATFORM_DEFAULTS: frozenset[str] = frozenset(
    _RULES.get("platform_default_variables", _PLATFORM_DEFAULT_FALLBACK)
)


def check_variables(wf: WizFile) -> list[Finding]:
    declared_names = {v.name for v in wf.variables.values()}
    referenced_names: set[str] = set()

    out: list[Finding] = []

    # WIZ201: undeclared references
    for utt in wf.utterances:
        for name in utt.referenced_vars:
            referenced_names.add(name)
            if name not in declared_names:
                out.append(Finding(
                    code="WIZ201",
                    severity=Severity.ERROR,
                    location=Location(entity="Utterance", id=str(utt.id), field="text"),
                    message=(
                        f"Utterance references undeclared variable {{{name}}}; "
                        f"will be spoken literally to the customer."
                    ),
                ))

    # WIZ202: declared but unused (skip platform-default variables)
    for var in wf.variables.values():
        if var.name in _PLATFORM_DEFAULTS:
            continue
        if var.name not in referenced_names:
            out.append(Finding(
                code="WIZ202",
                severity=Severity.WARNING,
                location=Location(entity="Variable", id=str(var.id), field="name"),
                message=f"Variable {{{var.name}}} is declared but never referenced.",
            ))

    return out
