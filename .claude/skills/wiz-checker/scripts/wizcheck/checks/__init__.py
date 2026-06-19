"""Check registry.

Each check is a callable (WizFile) -> list[Finding]. The registry is intentionally
hand-curated (not auto-discovered) so the running order is stable and explicit.
"""

from __future__ import annotations

from collections.abc import Callable

from wizcheck.checks.graph import check_graph
from wizcheck.checks.intents import check_intents
from wizcheck.checks.platform import check_platform
from wizcheck.checks.schema import check_schema
from wizcheck.checks.variables import check_variables
from wizcheck.ir import WizFile
from wizcheck.report import Finding

REGISTRY: dict[str, Callable[[WizFile], list[Finding]]] = {
    "schema": check_schema,
    "graph": check_graph,
    "variables": check_variables,
    "intents": check_intents,
    "platform": check_platform,
}


def get_check(name: str) -> Callable[[WizFile], list[Finding]]:
    if name not in REGISTRY:
        raise KeyError(f"Unknown check: {name!r}. Known checks: {sorted(REGISTRY)}")
    return REGISTRY[name]


def run_all_checks(wf: WizFile) -> list[Finding]:
    findings: list[Finding] = []
    for name in ["schema", "graph", "variables", "intents", "platform"]:
        findings.extend(REGISTRY[name](wf))
    return findings
