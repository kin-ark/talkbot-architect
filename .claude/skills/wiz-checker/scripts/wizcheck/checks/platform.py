"""Platform-constraint checks (WIZ400..WIZ499).

Facts sourced from the WIZ.AI manuals via the wizfacts package. These flag
values that deviate from documented platform behaviour. Kept in a dedicated
code range so manual-sourced findings are auditable apart from schema (0xx),
graph (1xx), variable (2xx), and intent (3xx) checks.
"""
from __future__ import annotations

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity
from wizfacts import load_facts

_FACTS = load_facts()
_SUPPORTED_LANGS = set(_FACTS.get("lang.supported"))


def check_platform(wf: WizFile) -> list[Finding]:
    out: list[Finding] = []

    # WIZ400: intent language not in the documented supported set.
    # Skip empty / non-ISO defensive defaults (e.g. "" or 0) — those are not
    # author-set ISO codes and would produce noise.
    for intent in wf.intents.values():
        lang = intent.language
        if not isinstance(lang, str) or not lang.strip():
            continue
        if lang not in _SUPPORTED_LANGS:
            out.append(Finding(
                code="WIZ400",
                severity=Severity.ERROR,
                location=Location(entity="Intent", id=str(intent.intent_id), field="language"),
                message=(
                    f"Intent language {lang!r} is not a documented supported language "
                    f"({sorted(_SUPPORTED_LANGS)})."
                ),
            ))

    return out
