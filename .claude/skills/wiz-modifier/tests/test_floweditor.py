"""Tests for wizmodifier.floweditor (Task 1 — FM-T1).

Characterisation tests lock the decoded shapes from a builder fixture so any
future drift in the node/SCS serialization fails loudly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# wiz-builder's scripts dir is a sibling skill, not on pythonpath.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "wiz-builder" / "scripts")
)

from wizbuilder.compile import compile_manifest  # noqa: E402
from wizmodifier.floweditor import FlowEditError, FlowEditor  # noqa: E402

FIX = Path(__file__).resolve().parents[2] / "wiz-builder" / "tests" / "fixtures"


def _build(tmp_path, manifest_name):
    out = tmp_path / "speech.json"
    compile_manifest(FIX / manifest_name, out)
    return json.loads(out.read_text(encoding="utf-8"))


def _uw(v):
    return json.loads(v) if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Fixture-level shape characterisation
# ---------------------------------------------------------------------------


def test_floweditor_reads_talk_branches(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    # The "greet" talk node wires Positive → check_status; other branches are unconnected.
    # out_edges returns only wired (routed) branches.
    # We pick the first talk node; at least "Positive" must be among its wired branches
    # because the manifest edges include {from: greet, branch: Positive, to: check_status}.
    talk = next(u for u, n in _uw(comp["details"]).items() if n["type"] == 1)
    branches = {b for b, _t in fe.out_edges(talk)}
    assert "Positive" in branches  # greet node wires Positive; other branches unrouted
    # every out-edge target must be a real node in this component
    for _b, tgt in fe.out_edges(talk):
        assert tgt in _uw(comp["details"])


def test_floweditor_resolve_uuid_and_label(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    u = next(iter(_uw(comp["details"])))
    assert fe.resolve({"uuid": u}) == u
    label = _uw(comp["details"])[u]["data"]["name"]
    # label may be duplicated ("Talk Node" x2) -> ambiguous must raise
    dupes = [n["data"]["name"] for n in _uw(comp["details"]).values()].count(label)
    if dupes > 1:
        with pytest.raises(FlowEditError, match="ambiguous|not unique"):
            fe.resolve({"label": label})


def test_floweditor_has_exit_and_flush_roundtrip(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    assert fe.has_exit() is True  # fixture ends in an Exit node
    fe.flush()  # no mutation -> re-encode must stay parseable
    assert isinstance(comp["details"], str)
    assert _uw(comp["details"])  # still decodes to a non-empty dict


def test_scs_link_is_locked(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    scs = _uw(doc["SentenceCutSpeech"])
    talk = next(u for u, n in _uw(comp["details"]).items() if n["type"] == 1)
    rows = fe.scs_rows_for(talk, scs)
    # componentUuid filter: every row belongs to this component
    assert rows and all(r.get("componentUuid") == comp["componentUuid"] for r in rows)
    # id filter: every row belongs specifically to this node (not just to the component)
    assert all(r.get("id") == talk for r in rows)


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


def test_node_type_returns_int(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    for uuid, node_obj in _uw(comp["details"]).items():
        assert fe.node_type(uuid) == node_obj["type"]


def test_node_type_raises_on_unknown_uuid(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    with pytest.raises(FlowEditError):
        fe.node_type("00000000-0000-0000-0000-000000000000")


def test_in_edges_consistency(tmp_path):
    """Every in-edge target must equal the queried uuid."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    for uuid in _uw(comp["details"]):
        for _src, _branch, tgt in fe.in_edges(uuid):
            assert tgt == uuid


def test_resolve_raises_on_bad_ref(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    with pytest.raises(FlowEditError, match="uuid|label"):
        fe.resolve({"bad_key": "x"})


def test_resolve_raises_on_missing_uuid(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    with pytest.raises(FlowEditError):
        fe.resolve({"uuid": "no-such-uuid"})


def test_resolve_unique_label(tmp_path):
    """A label that appears exactly once must resolve without error."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    details = _uw(comp["details"])
    # find a label that is unique
    from collections import Counter
    label_counts = Counter(n["data"]["name"] for n in details.values())
    unique_labels = [label for label, count in label_counts.items() if count == 1]
    if unique_labels:
        result = fe.resolve({"label": unique_labels[0]})
        expected = next(u for u, n in details.items() if n["data"]["name"] == unique_labels[0])
        assert result == expected


def test_unconnected_branches_talk_node_has_unconnected(tmp_path):
    """The greet talk node wires only Positive → check_status; Negative and
    Unclassified are unrouted, so unconnected_branches() must surface them.

    Fixture: manifest_conditional_assign.yaml
      edges: greet.Positive → check_status   (routed)
             greet.Negative                  (unrouted)
             greet.Unclassified              (unrouted)
    """
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    result = fe.unconnected_branches()
    # greet is the first type-1 node in details order
    talk = next(u for u, n in _uw(comp["details"]).items() if n["type"] == 1)
    unconnected_for_talk = [b for (u, b) in result if u == talk]
    # Negative is unrouted on greet; Unclassified is also unrouted
    assert "Negative" in unconnected_for_talk, (
        f"expected Negative to be unconnected on greet node; got {unconnected_for_talk}"
    )
    assert "Unclassified" in unconnected_for_talk, (
        f"expected Unclassified to be unconnected on greet node; got {unconnected_for_talk}"
    )
    # all entries are (str, str) tuples
    for item in result:
        assert len(item) == 2
        assert isinstance(item[0], str) and isinstance(item[1], str)


def test_flush_produces_compact_json(tmp_path):
    """flush() must use compact separators (no spaces) matching codec.encode."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = _uw(doc["BizSpeechComponent"])[0]
    fe = FlowEditor(comp)
    fe.flush()
    # compact JSON: no ": " or ", " separators
    assert " " not in comp["routes"] or comp["routes"] in ("[]", "{}")
    # details must round-trip cleanly
    details_rt = json.loads(comp["details"])
    assert isinstance(details_rt, dict)
    assert len(details_rt) == len(fe.details)
