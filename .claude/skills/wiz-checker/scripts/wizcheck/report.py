"""Finding, Report, and output rendering.

Findings are immutable data records. Report aggregates them. Terminal and JSON
rendering live as methods on Report (Tasks 10 and 11).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from io import StringIO

from rich.console import Console
from rich.table import Table


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


# Codes that block deployment even though WIZ accepts the import (code:0).
# `check.py --deploy` exits non-zero if any finding carries one of these,
# regardless of that finding's severity.
DEPLOY_BLOCKER_CODES = frozenset({
    "WIZ101", "WIZ107", "WIZ108", "WIZ109", "WIZ110", "WIZ303", "WIZ304", "WIZ305"
})


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

    def print_terminal(self) -> None:
        """Render directly to stdout (used by CLI). Uses a real terminal Console
        so table borders and colors render properly when stdout is a TTY."""
        self._render_to_console(Console())

    def to_terminal_string(self) -> str:
        """Render report as a plain-text string (no ANSI/box-drawing).

        Used by tests and consumers that need to capture output as text.
        """
        buf = StringIO()
        self._render_to_console(Console(file=buf, force_terminal=False, width=120))
        return buf.getvalue()

    def _render_to_console(self, console: Console) -> None:
        """Shared rendering logic for both terminal and string output."""
        console.print(f"[bold]wiz-checker[/bold] — {self.file}")
        console.print(
            f"Checks run: {', '.join(self.checks_run) if self.checks_run else '(none)'}"
        )
        if self.findings:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Code", width=8)
            table.add_column("Sev", width=8)
            table.add_column("Where", width=40)
            table.add_column("Message")
            for f in self.findings:
                where = f.location.entity
                if f.location.id:
                    where += f" {f.location.id}"
                if f.location.field:
                    where += f".{f.location.field}"
                sev_color = "red" if f.severity is Severity.ERROR else "yellow"
                table.add_row(
                    f.code,
                    f"[{sev_color}]{f.severity.value}[/{sev_color}]",
                    where,
                    f.message,
                )
            console.print(table)
        errs, warns = self.error_count(), self.warning_count()
        err_word = "error" if errs == 1 else "errors"
        warn_word = "warning" if warns == 1 else "warnings"
        console.print(f"\n[bold]{errs} {err_word}, {warns} {warn_word}[/bold]")

    def to_json_dict(self) -> dict:
        """Serialize report to a stable dictionary structure."""
        return {
            "file": self.file,
            "summary": {
                "errors": self.error_count(),
                "warnings": self.warning_count(),
                "checks_run": list(self.checks_run),
            },
            "findings": [
                {
                    "code": f.code,
                    "severity": f.severity.value,
                    "location": {
                        "entity": f.location.entity,
                        "id": f.location.id,
                        "field": f.location.field,
                    },
                    "message": f.message,
                }
                for f in self.findings
            ],
        }

    def to_json_string(self, indent: int = 2) -> str:
        """Serialize report to a JSON string."""
        return json.dumps(self.to_json_dict(), indent=indent, ensure_ascii=False)
