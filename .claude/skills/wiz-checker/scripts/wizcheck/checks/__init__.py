"""Check registry.

Each check is a callable (WizFile) -> list[Finding]. The registry is intentionally
hand-curated (not auto-discovered) so the running order is stable and explicit.
"""

from __future__ import annotations

from collections.abc import Callable

from wizcheck.checks.graph import check_graph
from wizcheck.checks.schema import check_schema
from wizcheck.ir import WizFile
from wizcheck.report import Finding


# Stub callables — replaced as each check is implemented in Tasks 15-16.
def _stub_variables(wf: WizFile) -> list[Finding]:
    return []


def _stub_intents(wf: WizFile) -> list[Finding]:
    return []


REGISTRY: dict[str, Callable[[WizFile], list[Finding]]] = {
    "schema": check_schema,
    "graph": check_graph,
    "variables": _stub_variables,
    "intents": _stub_intents,
}


def get_check(name: str) -> Callable[[WizFile], list[Finding]]:
    if name not in REGISTRY:
        raise KeyError(f"Unknown check: {name!r}. Known checks: {sorted(REGISTRY)}")
    return REGISTRY[name]


def run_all_checks(wf: WizFile) -> list[Finding]:
    findings: list[Finding] = []
    for name in ["schema", "graph", "variables", "intents"]:
        findings.extend(REGISTRY[name](wf))
    return findings
