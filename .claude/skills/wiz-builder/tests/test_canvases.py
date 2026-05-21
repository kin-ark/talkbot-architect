"""Tests for wizbuilder.canvases — apply_canvases step."""

from __future__ import annotations

import json
from uuid import UUID

from wizbuilder.canvases import apply_canvases
from wizbuilder.ids import IdMinter, manifest_hash_of
from wizbuilder.manifest import load_manifest


def test_apply_canvases_replaces_template_component(template_dict, fixture_path):
    """The single empty template BizSpeechComponent is replaced by manifest canvases."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    assert len(bsc) == 2
    names = {c["name"] for c in bsc}
    assert names == {"1. Greeting", "2. Closing"}


def test_apply_canvases_each_component_has_uuid(template_dict, fixture_path):
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    for comp in bsc:
        UUID(comp["componentUuid"])  # well-formed
        assert comp["parentUuid"] == "0"  # all canvas roots
        assert comp["branch"] == "dev"
        assert comp["category"] == 1


def test_apply_canvases_details_encodes_canvas_props(template_dict, fixture_path):
    """details is JSON-string dict keyed by envelope UUID; nodes at canvas/component/props/list."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")

    details = json.loads(greeting["details"])
    assert isinstance(details, dict)
    assert len(details) == 1
    envelope = next(iter(details.values()))
    nodes = envelope["canvas"]["component"]["props"]["list"]
    assert len(nodes) == 2
    labels = {n["label"] for n in nodes}
    assert labels == {"Greeting", "Pitch"}


def test_apply_canvases_root_node_has_empty_parent_id(template_dict, fixture_path):
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    nodes = next(iter(details.values()))["canvas"]["component"]["props"]["list"]
    root = next(n for n in nodes if n["label"] == "Greeting")
    assert root["parentId"] == ""


def test_apply_canvases_child_parent_resolves_to_root_uuid(template_dict, fixture_path):
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    nodes = next(iter(details.values()))["canvas"]["component"]["props"]["list"]
    root = next(n for n in nodes if n["label"] == "Greeting")
    child = next(n for n in nodes if n["label"] == "Pitch")
    assert child["parentId"] == root["uuid"]


def test_apply_canvases_node_uuids_are_deterministic(fixture_path, template_path):
    """Same manifest text yields same FlowNode UUIDs across runs."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))

    tpl1 = json.loads(template_path.read_text(encoding="utf-8"))
    minter1 = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(tpl1, m, minter1)

    tpl2 = json.loads(template_path.read_text(encoding="utf-8"))
    minter2 = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(tpl2, m, minter2)

    bsc1 = json.loads(tpl1["BizSpeechComponent"])
    bsc2 = json.loads(tpl2["BizSpeechComponent"])

    def collect_node_uuids(bsc):
        out = []
        for comp in bsc:
            det = json.loads(comp["details"])
            for env in det.values():
                for node in env["canvas"]["component"]["props"]["list"]:
                    out.append(node["uuid"])
        return sorted(out)

    assert collect_node_uuids(bsc1) == collect_node_uuids(bsc2)


def test_apply_canvases_sort_index_is_positional(template_dict, fixture_path):
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    nodes_obj = json.loads(greeting["details"])
    nodes_list = next(iter(nodes_obj.values()))["canvas"]["component"]["props"]["list"]
    by_label = {n["label"]: n for n in nodes_list}
    assert by_label["Greeting"]["sortIndex"] == 0
    assert by_label["Pitch"]["sortIndex"] == 1
