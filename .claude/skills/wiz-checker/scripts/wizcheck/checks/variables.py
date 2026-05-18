"""Variable consistency checks (WIZ200..WIZ299)."""

from __future__ import annotations

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity


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

    # WIZ202: declared but unused
    for var in wf.variables.values():
        if var.name not in referenced_names:
            out.append(Finding(
                code="WIZ202",
                severity=Severity.WARNING,
                location=Location(entity="Variable", id=str(var.id), field="name"),
                message=f"Variable {{{var.name}}} is declared but never referenced.",
            ))

    return out
