"""Variable consistency checks (WIZ200..WIZ299).

WIZ201: undeclared variable references in utterance text.
WIZ202: declared-but-unused USER-AUTHORED variables only (variableSource == 0).

Platform-managed variables (variableSource == 1) are exported on every WIZ.AI
dialogue regardless of whether the script author uses them; flagging them as
"unused" produces noise. textType is NOT used — real exports sometimes strip
textType from system variables. See schema/variable_rules.yaml.
"""

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

    # WIZ202: declared but unused — user-authored variables only.
    # variableSource == 1 marks platform/system-managed variables, which are
    # exported on every dialogue regardless of script usage. textType is NOT
    # used as a filter — real exports sometimes strip textType from system vars.
    for var in wf.variables.values():
        if var.variable_source == 1:
            continue  # platform-managed; skip
        if var.name not in referenced_names:
            out.append(Finding(
                code="WIZ202",
                severity=Severity.WARNING,
                location=Location(entity="Variable", id=str(var.id), field="name"),
                message=f"Variable {{{var.name}}} is declared but never referenced.",
            ))

    return out
