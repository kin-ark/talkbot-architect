"""Tests for checks.schema — schema-shape findings WIZ001..WIZ099."""

from __future__ import annotations

import json as _json
from uuid import UUID

from wizcheck.checks.schema import check_schema
from wizcheck.ir import (
    Component,
    Intent,
    Utterance,
    WizFile,
)
from wizcheck.parser import parse_dict
from wizcheck.report import Severity


def _wf(**overrides) -> WizFile:
    defaults = dict(
        raw={"BizSpeechComponent": [], "SpeechVariable": [], "SpeechIntent": [],
             "SentenceCutSpeech": [], "SpeechAudio": []},
        components={},
        variables={},
        intents={},
        utterances=(),
        audios={}, knowledge_bases={},
    )
    defaults.update(overrides)
    return WizFile(**defaults)


def _comp(category=1, branch="dev", raw=None) -> Component:
    return Component(
        uuid=UUID(int=1),
        speech_id=1,
        category=category,
        branch=branch,
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
        audios={}, knowledge_bases={},
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
    """A component with details='null' (empty canvas) fires WIZ006.

    Uses parse_dict so that wf.flow_model is populated — the check now reads
    flow_model.components[i].nodes instead of the old IR flow_nodes.
    """
    wf = parse_dict(_export_with_comp("null"))
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ006"), None)
    assert f is not None
    assert f.severity is Severity.WARNING
    assert "empty" in f.message.lower() or "no canvas" in f.message.lower()


def test_wiz006_skipped_when_canvas_has_nodes():
    """A component with >=1 node in flow_model does not fire WIZ006.

    Uses parse_dict with a new-format details dict (UUID-keyed envelope) so that
    wf.flow_model.components[i].nodes is non-empty.
    """
    new_format_details = {
        _NODE_UUID: {
            "type": 1,
            "name": "Greeting",
            "is_default": True,
            "data": {"list": [{"text": "Hello!"}]},
        }
    }
    wf = parse_dict(_export_with_comp(new_format_details))
    findings = check_schema(wf)
    assert not any(f.code == "WIZ006" for f in findings)



def test_wiz008_truncated_script_is_warning():
    """WIZ008 warns if Utterance text ends with '...'"""
    u = Utterance(
        id=UUID(int=200), component_uuid=UUID(int=3), text="This is truncated...",
        referenced_vars=(), raw={}
    )
    wf = _wf(utterances=(u,))
    findings = check_schema(wf)

    f = next((x for x in findings if x.code == "WIZ008"), None)
    assert f is not None
    assert f.severity is Severity.WARNING


# ---------------------------------------------------------------------------
# WIZ006 FlowModel-based tests — must use parse_dict so flow_model is populated
# ---------------------------------------------------------------------------

_COMP_UUID = "11111111-1111-4111-8111-111111111111"
_NODE_UUID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

_MINIMAL_EXPORT = {
    "BizSpeechComponent": [],
    "SpeechVariable": [],
    "SpeechIntent": [],
    "SentenceCutSpeech": [],
    "SpeechAudio": [],
}


def _export_with_comp(details) -> dict:
    """Minimal export dict with one component whose details= is the given value."""
    return {
        **_MINIMAL_EXPORT,
        "BizSpeechComponent": [
            {
                "componentUuid": _COMP_UUID,
                "speechId": 1,
                "category": 1,
                "branch": "dev",
                "createTime": 1700000000000,
                "updateTime": 1700000000000,
                "name": "TestComp",
                "details": details,
            }
        ],
    }


def test_wiz006_not_raised_for_populated_component():
    """A component with >=1 node in flow_model must NOT fire WIZ006.

    Real WIZ exports use a new-format details: a dict keyed by node UUID
    (no canvas.component.props.list nesting), so the old IR flow_nodes check
    would falsely fire WIZ006.  The FlowModel-based check must not.
    """
    # New-format details: top-level UUID key -> envelope with type/name/data.
    # build_flow_model iterates these keys as nodes → comp.nodes is non-empty.
    new_format_details = {
        _NODE_UUID: {
            "type": 1,
            "name": "Greeting",
            "is_default": True,
            "data": {"list": [{"text": "Hello!"}]},
        }
    }
    wf = parse_dict(_export_with_comp(new_format_details))
    findings = check_schema(wf)
    assert not any(f.code == "WIZ006" for f in findings), (
        f"WIZ006 falsely fired for a populated component: "
        f"{[f for f in findings if f.code == 'WIZ006']}"
    )


def test_wiz006_raised_for_empty_component():
    """A component with details='null' (empty canvas) must fire WIZ006."""
    # Real WIZ exports emit details: "null" for empty/template components.
    wf = parse_dict(_export_with_comp("null"))
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ006"), None)
    assert f is not None, "WIZ006 must fire for a component with details='null'"
    assert f.severity is Severity.WARNING


# ---------------------------------------------------------------------------
# WIZ007: FlowModel-based tests — parse_dict so flow_model is populated.
# Verify WIZ007 fires correctly when reading from FlowModelNode.data.
# ---------------------------------------------------------------------------


def _export_with_node(node_name: str, node_type: int, sentence_text: str | None) -> dict:
    """Build a minimal export with one node whose sentenceText is given."""
    node_uuid = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    data_dict: dict = {
        "list": [{"text": sentence_text}] if sentence_text is not None else [],
        "all_client_intent": [],
        "node_variables": [],
        "allow_jump_knowledges": [],
    }
    if sentence_text is not None:
        data_dict["sentenceText"] = sentence_text
    details = {
        node_uuid: {
            "type": node_type,
            "name": node_name,
            "is_default": True,
            "data": data_dict,
        }
    }
    return {
        "BizSpeechComponent": [
            {
                "componentUuid": _COMP_UUID,
                "speechId": 1,
                "category": 1,
                "branch": "dev",
                "createTime": 1700000000000,
                "updateTime": 1700000000000,
                "name": "TestComp",
                "details": details,
                "routes": _json.dumps({}),
            }
        ],
        "BizKnowledgeInfo": [],
        "SpeechVariable": [],
        "SpeechIntent": [],
        "SentenceCutSpeech": [],
        "SpeechAudio": [],
    }


def test_wiz007_flowmodel_wait_blank_fires():
    """WIZ007: Wait node with sentenceText='blank' → WIZ007."""
    wf = parse_dict(_export_with_node("Wait", 1, "blank"))
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ007"), None)
    assert f is not None, f"Expected WIZ007 but got: {[x.code for x in findings]}"
    assert f.severity is Severity.WARNING
    assert "Wait" in f.message


def test_wiz007_flowmodel_exit_empty_fires():
    """WIZ007: Exit node with sentenceText='' → WIZ007."""
    wf = parse_dict(_export_with_node("Exit", 2, ""))
    findings = check_schema(wf)
    f = next((x for x in findings if x.code == "WIZ007"), None)
    assert f is not None, f"Expected WIZ007 but got: {[x.code for x in findings]}"
    assert f.severity is Severity.WARNING
    assert "Exit" in f.message


def test_wiz007_flowmodel_wait_with_real_script_no_fire():
    """WIZ007: Wait node with a real script → no WIZ007."""
    wf = parse_dict(_export_with_node("Wait", 1, "Please hold on."))
    findings = check_schema(wf)
    assert not any(x.code == "WIZ007" for x in findings)


def test_wiz007_flowmodel_other_node_name_no_fire():
    """WIZ007: node with sentenceText='blank' but not named Wait/Exit → no WIZ007."""
    wf = parse_dict(_export_with_node("Greeting", 1, "blank"))
    findings = check_schema(wf)
    assert not any(x.code == "WIZ007" for x in findings)
