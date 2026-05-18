"""Tests for wizcheck.report (Finding, Report, renderers)."""

from __future__ import annotations

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
