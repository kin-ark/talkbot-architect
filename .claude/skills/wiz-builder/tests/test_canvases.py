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


def test_apply_canvases_details_has_real_node_shape(template_dict, fixture_path):
    """details is a JSON-string dict keyed by node_uuid; each value has real node fields."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")

    details = json.loads(greeting["details"])
    assert isinstance(details, dict)
    # New shape: keyed by node_uuid, not envelope_uuid
    # Greeting canvas has 2 nodes
    assert len(details) == 2
    for node_uuid, node_obj in details.items():
        assert "canvas" in node_obj
        assert "data" in node_obj
        assert "name" in node_obj
        assert node_obj["name"] == "Talk Node"
        assert "type" in node_obj
        assert "is_default" in node_obj
        assert "data_extra" in node_obj


def test_apply_canvases_node_prompts_in_details(template_dict, fixture_path):
    """Nodes in details carry their prompt text in data.list and data.dialog_list."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    texts = {node["data"]["list"][0] for node in details.values()}
    assert texts == {"Greeting", "Pitch"}


def test_apply_canvases_entry_node_is_default(template_dict, fixture_path):
    """The entry node (no incoming edge) has is_default=True."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    entry_nodes = [n for n in details.values() if n["is_default"] is True]
    assert len(entry_nodes) == 1
    assert entry_nodes[0]["data"]["list"][0] == "Greeting"


def test_apply_canvases_non_entry_node_not_default(template_dict, fixture_path):
    """A node targeted by an edge has is_default=False."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    pitch_node = next(n for n in details.values() if n["data"]["list"][0] == "Pitch")
    assert pitch_node["is_default"] is False


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
            out.extend(det.keys())
        return sorted(out)

    assert collect_node_uuids(bsc1) == collect_node_uuids(bsc2)


def test_apply_canvases_inbound_ports_has_entry_node(template_dict, fixture_path):
    """inboundPorts is a JSON list with one entry per entry node."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    for comp in bsc:
        inbound = json.loads(comp["inboundPorts"])
        assert isinstance(inbound, list)
        assert len(inbound) >= 1
        for port in inbound:
            assert "uuid" in port
            assert "name" in port
            assert port["is_default"] is True


def test_apply_canvases_routes_is_dict(template_dict, fixture_path):
    """routes is a JSON-string dict keyed by node_uuid."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    for comp in bsc:
        routes = json.loads(comp["routes"])
        assert isinstance(routes, dict)


def test_apply_canvases_routes_wires_edge(template_dict, fixture_path):
    """The Unclassified edge from greet-root → greet-pitch is wired in routes."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    routes = json.loads(greeting["routes"])

    entry_uuid = next(uuid for uuid, n in details.items() if n["is_default"])
    entry_routes = routes[entry_uuid]  # should have one port wired
    assert len(entry_routes) == 1, "entry node should have one outgoing wired route (Unclassified)"


def test_apply_canvases_sentence_cut_speech_populated(template_dict, fixture_path):
    """SentenceCutSpeech is set on the template with one row per node."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    scs = json.loads(template_dict["SentenceCutSpeech"])
    assert isinstance(scs, list)
    # 2 nodes in Greeting + 1 node in Closing = 3 total
    assert len(scs) == 3
    for row in scs:
        assert "sentenceText" in row
        assert "componentUuid" in row
        assert "speechId" in row


def test_apply_canvases_component_has_real_export_keys(template_dict, fixture_path):
    """Each BizSpeechComponent entry must include the structural keys present in real WIZ exports."""
    m = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    # All components share these structural keys
    for comp in bsc:
        for key in ("inboundPorts", "routes", "sourceUuid", "topFloorDetails"):
            assert key in comp, f"Component '{comp['name']}' missing key '{key}'"
        # routes must be a dict (not "[]")
        routes = json.loads(comp["routes"])
        assert isinstance(routes, dict)
        assert comp["sourceUuid"] == ""
        assert comp["topFloorDetails"] == "{}"
    # outboundPorts and nluConf are only on component[0] in real WIZ exports
    assert bsc[0]["outboundPorts"] == "[]"
    assert bsc[0]["nluConf"] == "{}"


def test_apply_canvases_secondary_strips_template_keys(template_dict, fixture_path):
    """Secondary BSC entries (index>0) must not carry template-only and first-comp-only keys."""
    _KEYS_TO_STRIP = {"createBy", "createTime", "language", "nluConf", "outboundPorts", "updateBy"}

    manifest = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))
    result = apply_canvases(template_dict, manifest, minter)

    comps = json.loads(result["BizSpeechComponent"])
    assert len(comps) == 2

    comp1_keys = set(comps[1].keys())
    leaked = _KEYS_TO_STRIP & comp1_keys
    assert not leaked, (
        f"secondary BSC entry should not have template-only keys, but found: {leaked}"
    )
