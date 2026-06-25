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
    for _node_uuid, node_obj in details.items():
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
    """Each BizSpeechComponent entry must include the structural keys present in real WIZ exports."""  # noqa: E501
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
        # topFloorDetails is a JSON-encoded list; "{}" fails WIZ import once nodes exist
        assert comp["topFloorDetails"] == "[]"
    # outboundPorts and nluConf are only on component[0] in real WIZ exports
    assert bsc[0]["outboundPorts"] == "[]"
    assert bsc[0]["nluConf"] == "{}"


def test_apply_canvases_secondary_strips_template_keys(template_dict, fixture_path):
    """Secondary BSC entries (index>0) must not carry template-only and first-comp-only keys."""
    _KEYS_TO_STRIP = {"createBy", "createTime", "language", "nluConf", "outboundPorts", "updateBy"}

    manifest = load_manifest(fixture_path("manifest_multi_canvas.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))
    result, _uuid_map = apply_canvases(template_dict, manifest, minter)

    comps = json.loads(result["BizSpeechComponent"])
    assert len(comps) == 2

    comp1_keys = set(comps[1].keys())
    leaked = _KEYS_TO_STRIP & comp1_keys
    assert not leaked, (
        f"secondary BSC entry should not have template-only keys, but found: {leaked}"
    )


# ---------------------------------------------------------------------------
# Task 2: exit + transfer node integration through apply_canvases
# ---------------------------------------------------------------------------


def test_apply_canvases_exit_node_topfloordetails(template_dict, fixture_path):
    """A canvas with an exit node must have one row in topFloorDetails (type 2)."""
    m = load_manifest(fixture_path("manifest_exit_transfer.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])

    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    tfd = json.loads(greeting["topFloorDetails"])
    assert isinstance(tfd, list)
    assert len(tfd) == 1, "exit canvas must have exactly one topFloorDetails row"
    row = tfd[0]
    assert row["type"] == 2
    assert row["is_transfer"] == 0
    assert row["dialog_list"][0]["text"] == "Goodbye and thanks"


def test_apply_canvases_transfer_node_topfloordetails_empty(template_dict, fixture_path):
    """A canvas with only a transfer node must have topFloorDetails=[] (type 13 excluded)."""
    m = load_manifest(fixture_path("manifest_exit_transfer.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])

    xfer_canvas = next(c for c in bsc if c["name"] == "2. Transfer Canvas")
    tfd = json.loads(xfer_canvas["topFloorDetails"])
    assert tfd == [], "transfer canvas topFloorDetails must be []"


def test_apply_canvases_exit_node_props_list_contains_all_canvases(template_dict, fixture_path):
    """The exit node canvas.component.props.list must list all canvases (component nav)."""
    m = load_manifest(fixture_path("manifest_exit_transfer.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])

    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    exit_node = next(v for v in details.values() if v["type"] == 2)
    props_list = exit_node["canvas"]["component"]["props"]["list"]

    # Must list all 2 canvases by name
    labels = [item["label"] for item in props_list]
    assert set(labels) == {"1. Greeting", "2. Transfer Canvas"}
    # UUIDs must be valid and match component UUIDs
    comp_uuids = {c["componentUuid"] for c in bsc}
    for item in props_list:
        assert item["componentUuid"] in comp_uuids
        assert item["uuid"] == item["componentUuid"]


def test_apply_canvases_exit_node_no_ports(template_dict, fixture_path):
    """Exit node canvas must have no 'ports' key (terminal)."""
    m = load_manifest(fixture_path("manifest_exit_transfer.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])

    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    exit_node = next(v for v in details.values() if v["type"] == 2)
    assert "ports" not in exit_node["canvas"]


def test_apply_canvases_exit_not_in_inbound_ports(template_dict, fixture_path):
    """Exit node must NOT appear in inboundPorts; only the Talk entry node does."""
    m = load_manifest(fixture_path("manifest_exit_transfer.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])

    greeting = next(c for c in bsc if c["name"] == "1. Greeting")
    details = json.loads(greeting["details"])
    exit_uuid = next(k for k, v in details.items() if v["type"] == 2)

    inbound = json.loads(greeting["inboundPorts"])
    inbound_uuids = [p["uuid"] for p in inbound]
    assert exit_uuid not in inbound_uuids
    assert len(inbound) == 1  # only the Talk entry node


# ---------------------------------------------------------------------------
# Task 3: goto_component (type 4) integration through apply_canvases
# ---------------------------------------------------------------------------


def test_apply_canvases_goto_appoint_node_id_resolves_to_target_uuid(template_dict, fixture_path):
    """The goto node's data.appoint_node_id must equal canvas B's pre-minted componentUuid."""
    m = load_manifest(fixture_path("manifest_goto.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])

    # canvas A is the one with the goto node
    canvas_a = next(c for c in bsc if c["name"] == "1. A Canvas")
    canvas_b = next(c for c in bsc if c["name"] == "2. B Canvas")
    target_uuid = canvas_b["componentUuid"]

    details = json.loads(canvas_a["details"])
    goto_node = next(v for v in details.values() if v["type"] == 4)
    assert goto_node["data"]["appoint_node_id"] == target_uuid
    assert goto_node["data"]["specificComponentName"] == "2. B Canvas"


def test_apply_canvases_goto_envelope_type_4(template_dict, fixture_path):
    """The goto node envelope type must be 4."""
    m = load_manifest(fixture_path("manifest_goto.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    canvas_a = next(c for c in bsc if c["name"] == "1. A Canvas")
    details = json.loads(canvas_a["details"])
    goto_node = next(v for v in details.values() if v["type"] == 4)
    assert goto_node["data"]["type"] == 4


def test_apply_canvases_goto_is_terminal(template_dict, fixture_path):
    """The goto node canvas has no 'ports' key and routes[goto_uuid]={}."""
    m = load_manifest(fixture_path("manifest_goto.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    canvas_a = next(c for c in bsc if c["name"] == "1. A Canvas")
    details = json.loads(canvas_a["details"])
    routes = json.loads(canvas_a["routes"])
    goto_uuid = next(k for k, v in details.items() if v["type"] == 4)
    assert "ports" not in details[goto_uuid]["canvas"]
    assert routes[goto_uuid] == {}


def test_apply_canvases_goto_top_floor_details(template_dict, fixture_path):
    """Canvas A (with goto node) must have one topFloorDetails row of type 4."""
    m = load_manifest(fixture_path("manifest_goto.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    canvas_a = next(c for c in bsc if c["name"] == "1. A Canvas")
    tfd = json.loads(canvas_a["topFloorDetails"])
    assert len(tfd) == 1
    assert tfd[0]["type"] == 4
    assert tfd[0]["appoint_node_id"] != ""


def test_apply_canvases_goto_no_scs_row(template_dict, fixture_path):
    """Goto node must NOT produce a SentenceCutSpeech row.

    manifest_goto has:
      - Canvas A: Talk(entry) + goto → 1 SCS row (Talk only; goto emits none)
      - Canvas B: Talk(entry) + exit → 2 SCS rows (Talk + exit both emit SCS)
    Total = 3 SCS rows.  The goto node's uuid must not appear in any SCS row.
    """
    m = load_manifest(fixture_path("manifest_goto.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_canvases(template_dict, m, minter)
    bsc = json.loads(template_dict["BizSpeechComponent"])
    canvas_a = next(c for c in bsc if c["name"] == "1. A Canvas")
    details = json.loads(canvas_a["details"])
    goto_uuid = next(k for k, v in details.items() if v["type"] == 4)

    scs = json.loads(template_dict["SentenceCutSpeech"])
    # 3 total: Talk-A + Talk-B + Exit-B; goto produces none
    assert len(scs) == 3
    scs_ids = {row["id"] for row in scs}
    assert goto_uuid not in scs_ids
