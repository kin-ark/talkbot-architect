"""Tests for wizcheck.report (Finding, Report, renderers)."""

from __future__ import annotations

import json

from wizcheck.report import Finding, Location, Report, Severity


def test_finding_holds_code_severity_location_message():
    loc = Location(entity="Utterance", id="abc", field="text")
    f = Finding(code="WIZ201", severity=Severity.ERROR, location=loc, message="boom")
    assert f.code == "WIZ201"
    assert f.severity is Severity.ERROR
    assert f.location.entity == "Utterance"


def test_report_aggregates_findings():
    r = Report(file="x.json")
    r.add(Finding("WIZ001", Severity.ERROR, Location("WizFile", None, None), "a"))
    r.add(Finding("WIZ100", Severity.WARNING, Location("FlowNode", "u", None), "b"))
    assert r.error_count() == 1
    assert r.warning_count() == 1
    assert len(r.findings) == 2


def test_report_counts_only_relevant_severities():
    r = Report(file="x.json")
    r.add(Finding("WIZ001", Severity.ERROR, Location("WizFile", None, None), "a"))
    r.add(Finding("WIZ002", Severity.ERROR, Location("WizFile", None, None), "b"))
    assert r.error_count() == 2
    assert r.warning_count() == 0


def test_report_with_no_findings_is_clean():
    r = Report(file="x.json")
    assert r.error_count() == 0
    assert r.warning_count() == 0
    assert r.is_clean() is True


def test_report_to_terminal_contains_filename():
    r = Report(file="speech.json")
    output = r.to_terminal_string()
    assert "speech.json" in output


def test_report_to_terminal_shows_finding_counts():
    r = Report(file="speech.json")
    r.add(Finding("WIZ001", Severity.ERROR, Location("WizFile", None, None), "boom"))
    r.add(Finding("WIZ002", Severity.WARNING, Location("WizFile", None, None), "meh"))
    output = r.to_terminal_string()
    assert "1 error" in output or "errors: 1" in output.lower() or "1 errors" in output
    assert "1 warning" in output or "warnings: 1" in output.lower() or "1 warnings" in output


def test_report_to_terminal_shows_each_finding_code():
    r = Report(file="speech.json")
    r.add(Finding("WIZ201", Severity.ERROR, Location("Utterance", "abc", "text"),
                  "Undeclared variable {Name}"))
    output = r.to_terminal_string()
    assert "WIZ201" in output
    assert "Undeclared variable" in output


def test_report_to_json_dict_has_stable_shape():
    r = Report(file="speech.json", checks_run=["schema", "graph"])
    r.add(Finding(
        "WIZ201",
        Severity.ERROR,
        Location("Utterance", "abc-uuid", "text"),
        "Undeclared variable {Name}",
    ))
    d = r.to_json_dict()
    assert d == {
        "file": "speech.json",
        "summary": {"errors": 1, "warnings": 0, "checks_run": ["schema", "graph"]},
        "findings": [
            {
                "code": "WIZ201",
                "severity": "error",
                "location": {"entity": "Utterance", "id": "abc-uuid", "field": "text"},
                "message": "Undeclared variable {Name}",
            }
        ],
    }


def test_report_to_json_string_is_valid_json():
    r = Report(file="x.json")
    s = r.to_json_string()
    parsed = json.loads(s)
    assert parsed["file"] == "x.json"
