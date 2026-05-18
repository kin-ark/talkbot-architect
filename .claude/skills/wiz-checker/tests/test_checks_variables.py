"""Tests for checks.variables — variable consistency WIZ200..WIZ299."""

from __future__ import annotations

from uuid import UUID

from wizcheck.checks.variables import check_variables
from wizcheck.ir import FlowGraph, Utterance, Variable, WizFile
from wizcheck.report import Severity


def _wf(variables: dict | None = None, utterances: tuple = ()) -> WizFile:
    return WizFile(
        raw={},
        components={},
        variables=variables or {},
        intents={},
        utterances=utterances,
        audios={},
        flow=FlowGraph(),
    )


def test_wiz201_undeclared_variable_is_error():
    u = Utterance(
        id=UUID(int=1),
        component_uuid=UUID(int=2),
        text="Halo {Name}",
        referenced_vars=("Name",),
        raw={},
    )
    wf = _wf(variables={}, utterances=(u,))
    findings = check_variables(wf)
    f = next((x for x in findings if x.code == "WIZ201"), None)
    assert f is not None
    assert f.severity is Severity.ERROR
    assert "Name" in f.message


def test_wiz201_declared_variable_does_not_warn():
    v = Variable(id=1, name="Name", text_type="DEFAULT", raw={})
    u = Utterance(
        id=UUID(int=10), component_uuid=UUID(int=11),
        text="Halo {Name}", referenced_vars=("Name",), raw={},
    )
    wf = _wf(variables={1: v}, utterances=(u,))
    findings = check_variables(wf)
    assert not any(f.code == "WIZ201" for f in findings)


def test_wiz202_still_fires_for_custom_unused():
    """A custom variable (text_type='') that is unused fires WIZ202."""
    v = Variable(id=1, name="CustomLoyaltyTier", text_type="", raw={})
    wf = _wf(variables={1: v}, utterances=())
    findings = check_variables(wf)
    f = next((x for x in findings if x.code == "WIZ202"), None)
    assert f is not None
    assert f.severity is Severity.WARNING
    assert "CustomLoyaltyTier" in f.message


def test_wiz202_used_variable_does_not_warn():
    v = Variable(id=1, name="CustomerLoyaltyTier", text_type="DEFAULT", raw={})
    u = Utterance(
        id=UUID(int=20), component_uuid=UUID(int=21),
        text="{CustomerLoyaltyTier}", referenced_vars=("CustomerLoyaltyTier",), raw={},
    )
    wf = _wf(variables={1: v}, utterances=(u,))
    findings = check_variables(wf)
    assert not any(f.code == "WIZ202" for f in findings)


def test_wiz202_skips_variable_with_system_default_text_type():
    """text_type='DEFAULT' is a platform-managed variable; unused is OK."""
    v = Variable(id=1, name="Greeting", text_type="DEFAULT", raw={})
    wf = _wf(variables={1: v}, utterances=())
    findings = check_variables(wf)
    assert not any(f.code == "WIZ202" for f in findings)


def test_wiz202_skips_variable_with_phone_text_type():
    """text_type='PHONE' is platform-managed; unused is OK."""
    v = Variable(id=1, name="Phone", text_type="PHONE", raw={})
    wf = _wf(variables={1: v}, utterances=())
    findings = check_variables(wf)
    assert not any(f.code == "WIZ202" for f in findings)


def test_wiz202_skips_variable_with_none_text_type():
    """text_type=None is platform-managed (legacy); unused is OK."""
    v = Variable(id=1, name="Follow-up Stage", text_type=None, raw={})
    wf = _wf(variables={1: v}, utterances=())
    findings = check_variables(wf)
    assert not any(f.code == "WIZ202" for f in findings)


def test_one_finding_per_undeclared_reference_per_utterance():
    u = Utterance(
        id=UUID(int=30), component_uuid=UUID(int=31),
        text="{A} {B}", referenced_vars=("A", "B"), raw={},
    )
    wf = _wf(variables={}, utterances=(u,))
    findings = [f for f in check_variables(wf) if f.code == "WIZ201"]
    assert len(findings) == 2
