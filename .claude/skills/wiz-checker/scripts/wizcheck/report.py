"""Finding, Report, and output rendering.

Findings are immutable data records. Report aggregates them. Terminal and JSON
rendering live as methods on Report (Tasks 10 and 11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Location:
    """Where in the file the finding applies."""

    entity: str  # e.g. "Utterance", "Component", "FlowNode", "WizFile"
    id: str | None  # entity identifier, stringified
    field: str | None  # optional field path, e.g. "text"


@dataclass(frozen=True)
class Finding:
    code: str  # e.g. "WIZ201"
    severity: Severity
    location: Location
    message: str


@dataclass
class Report:
    """Mutable aggregator of Findings produced by a CLI run."""

    file: str
    findings: list[Finding] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def extend(self, findings: list[Finding]) -> None:
        self.findings.extend(findings)

    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity is Severity.ERROR)

    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity is Severity.WARNING)

    def is_clean(self) -> bool:
        return self.error_count() == 0 and self.warning_count() == 0
