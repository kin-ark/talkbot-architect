"""Tests for checks.schema — schema-shape findings WIZ001..WIZ099."""

from __future__ import annotations

from uuid import UUID

from wizcheck.checks.schema import check_schema
from wizcheck.ir import (
    Component,
    ComponentDetails,
    FlowGraph,
    FlowNode,
    Intent,
    Utterance,
    WizFile,
)
from wizcheck.report import Severity


def _wf(**overrides) -> WizFile:
    defaults = dict(
        raw={"BizSpeechComponent": [], "SpeechVariable": [], "SpeechIntent": [],
             "SentenceCutSpeech": [], "SpeechAudio": []},
        components={},
        variables={},
        intents={},
        utterances=(),
        audios={},
        flow=FlowGraph(),
    )
    defaults.update(overrides)
    return WizFile(**defaults)


def _comp(category=1, branch="dev", raw=None) -> Component:
    return Component(
        uuid=UUID(int=1),
        speech_id=1,
        category=category,
        branch=branch,
        details=ComponentDetails(flow_nodes={}, root_uuids=()),
        raw=raw if raw is not None else {"createTime": 1700000000000, "updateTime": 1700000000000},
    )


def test_wiz001_required_top_level_missing():
    wf = WizFile(
        raw={"SpeechVariable": [], "SpeechIntent": [],
             "SentenceCutSpeech": [], "SpeechAudio": []},  # missing BizSpeechComponent
        components={},
        variables={},
        intents={},
        utterances=(),
        audios={},
        flow=FlowGraph(),
    )
    findings = check_schema(wf)
    codes = {f.code for f in findings}
    assert "WIZ001" in codes
    f = next(x for x in findings if x.code == "WIZ001")
    assert f.severity is Severity.ERROR
    assert "BizSpeechComponent" in f.message


def test_wiz002_unknown_component_category_is_warning():
    comp = _comp(category=99)
    wf = _wf(components={comp.uuid: comp})
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ002"), None)
    assert f is not None
    assert f.severity is Severity.WARNING


def test_wiz003_unknown_branch_is_warning():
    comp = _comp(branch="staging")
    wf = _wf(components={comp.uuid: comp})
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ003"), None)
    assert f is not None
    assert f.severity is Severity.WARNING


def test_wiz004_unknown_intent_language_is_warning():
    intent = Intent(
        intent_id=1, name="Negative", language="ZZZ",
        keywords=(), user_responses=(), raw={},
    )
    wf = _wf(intents={1: intent})
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ004"), None)
    assert f is not None
    assert f.severity is Severity.WARNING


def test_wiz005_zero_timestamp_is_error():
    comp = _comp(raw={"createTime": 0, "updateTime": 0})
    wf = _wf(components={comp.uuid: comp})
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ005"), None)
    assert f is not None
    assert f.severity is Severity.ERROR


def test_known_category_produces_no_finding():
    comp = _comp(category=1, branch="dev")
    wf = _wf(components={comp.uuid: comp})
    findings = check_schema(wf)
    codes = {f.code for f in findings}
    assert "WIZ002" not in codes
    assert "WIZ003" not in codes


def test_wiz004_empty_language_does_not_fire():
    """Empty-string language is treated as absent, not unknown."""
    intent = Intent(
        intent_id=1, name="Negative", language="",
        keywords=(), user_responses=(), raw={},
    )
    wf = _wf(intents={1: intent})
    findings = check_schema(wf)
    assert not any(f.code == "WIZ004" for f in findings)


def test_wiz004_none_language_does_not_fire():
    """None language is treated as absent, not unknown."""
    intent = Intent(
        intent_id=1, name="Negative", language=None,
        keywords=(), user_responses=(), raw={},
    )
    wf = _wf(intents={1: intent})
    findings = check_schema(wf)
    assert not any(f.code == "WIZ004" for f in findings)


def test_wiz006_empty_canvas_is_warning():
    """A component with zero FlowNodes (empty canvas / template) fires WIZ006."""
    comp = Component(
        uuid=UUID(int=1),
        speech_id=1,
        category=1,
        branch="dev",
        details=ComponentDetails(flow_nodes={}, root_uuids=()),
        raw={"createTime": 1700000000000, "updateTime": 1700000000000, "name": "Empty"},
    )
    wf = _wf(components={comp.uuid: comp})
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ006"), None)
    assert f is not None
    assert f.severity is Severity.WARNING
    assert "empty" in f.message.lower() or "no canvas" in f.message.lower()


def test_wiz006_skipped_when_canvas_has_nodes():
    """A component with at least one FlowNode does not fire WIZ006."""
    node = FlowNode(
        uuid=UUID(int=99), parent_uuid=None, label="Greeting", sort_index=0, raw={},
    )
    comp = Component(
        uuid=UUID(int=2),
        speech_id=1,
        category=1,
        branch="dev",
        details=ComponentDetails(flow_nodes={UUID(int=99): node}, root_uuids=(UUID(int=99),)),
        raw={"createTime": 1700000000000, "updateTime": 1700000000000, "name": "NonEmpty"},
    )
    wf = _wf(components={comp.uuid: comp})
    findings = check_schema(wf)
    assert not any(f.code == "WIZ006" for f in findings)


def test_wiz106_empty_wait_script_is_warning():
    """WIZ106 warns if Wait or Exit node has sentenceText 'blank' or ''."""
    node = FlowNode(
        uuid=UUID(int=106), parent_uuid=None, label="Wait", sort_index=0,
        raw={"sentenceText": "blank"}
    )
    node2 = FlowNode(
        uuid=UUID(int=107), parent_uuid=None, label="Exit", sort_index=1,
        raw={"sentenceText": ""}
    )
    comp = Component(
        uuid=UUID(int=3), speech_id=1, category=1, branch="dev",
        details=ComponentDetails(flow_nodes={node.uuid: node, node2.uuid: node2}, root_uuids=(node.uuid,)),
        raw={"createTime": 1700000000000, "updateTime": 1700000000000},
    )
    wf = _wf(components={comp.uuid: comp})
    findings = check_schema(wf)
    
    f_wait = next((x for x in findings if x.code == "WIZ106" and x.location.id == str(node.uuid)), None)
    assert f_wait is not None
    assert f_wait.severity is Severity.WARNING

    f_exit = next((x for x in findings if x.code == "WIZ106" and x.location.id == str(node2.uuid)), None)
    assert f_exit is not None
    assert f_exit.severity is Severity.WARNING


def test_wiz107_truncated_script_is_warning():
    """WIZ107 warns if Utterance text ends with '...'"""
    u = Utterance(
        id=UUID(int=200), component_uuid=UUID(int=3), text="This is truncated...",
        referenced_vars=(), raw={}
    )
    wf = _wf(utterances=(u,))
    findings = check_schema(wf)
    
    f = next((x for x in findings if x.code == "WIZ107"), None)
    assert f is not None
    assert f.severity is Severity.WARNING
