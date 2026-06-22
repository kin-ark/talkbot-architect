import sys
from pathlib import Path

import pytest

# wiz-builder's scripts dir is a sibling skill, not on pythonpath.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "wiz-builder" / "scripts")
)

from wizbuilder.ids import IdMinter  # noqa: E402
from wizmodifier import codec  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops import structure  # noqa: E402
from wizmodifier.ops._bsc import get_components  # noqa: E402

MINTER = IdMinter(manifest_hash="deadbeef")


def test_add_bsc_keys_defaults(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    structure.add_bsc_keys(b, {"component": 0}, MINTER)
    comp = get_components(b)[0]
    for k, v in {
        "inboundPorts": "[]", "outboundPorts": "[]", "routes": "[]",
        "nluConf": "{}", "sourceUuid": "", "topFloorDetails": "[]",
    }.items():
        assert comp[k] == v


def test_populate_details_builds_envelope(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "n1", "prompt": "Greeting"}]},
        MINTER,
    )
    comp = get_components(b)[0]
    details = codec.decode(comp["details"])
    node_obj = next(iter(details.values()))
    # New real node shape: top-level has canvas + data keys (not props.list)
    assert "data" in node_obj
    assert node_obj["data"]["dialog_list"][0]["text"] == "Greeting"
    assert "canvas" in node_obj


def test_add_component_appends_entry(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    before = len(get_components(b))
    structure.add_component(b, {"name": "Second Canvas"}, MINTER)
    comps = get_components(b)
    assert len(comps) == before + 1
    new = comps[-1]
    assert new["name"] == "Second Canvas"
    assert new["details"] == "null"  # no nodes given
    assert new["parentUuid"] == "0"
    assert new["sortIndex"] == before + 1


def test_add_component_with_nodes_populates_details(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    structure.add_component(
        b,
        {"name": "Flow", "nodes": [{"id": "root", "prompt": "Open"}]},
        MINTER,
    )
    new = get_components(b)[-1]
    assert new["details"] != "null"
    details = codec.decode(new["details"])
    node_obj = next(iter(details.values()))
    # New real node shape: top-level has data key
    assert "data" in node_obj
    assert node_obj["data"]["dialog_list"][0]["text"] == "Open"


def test_add_component_strips_template_keys_from_secondary(baseline_dict):
    """Secondary components (index>0) must not carry template-only and first-comp-only keys."""
    _KEYS_TO_STRIP = {"createBy", "createTime", "language", "nluConf", "outboundPorts", "updateBy"}

    b = InputBundle(data=baseline_dict, speech_name="s.json")

    # Ensure baseline component 0 has at least some of these keys (it inherits from template)
    comps_before = get_components(b)
    comp0_keys = set(comps_before[0].keys())
    # Skip test if baseline doesn't have any of these keys (already clean)
    if not (_KEYS_TO_STRIP & comp0_keys):
        pytest.skip("baseline has none of the expected strippable keys")

    structure.add_component(b, {"name": "2. Canvas"}, MINTER)

    comps = get_components(b)
    comp1_keys = set(comps[1].keys())
    leaked = _KEYS_TO_STRIP & comp1_keys
    assert not leaked, (
        f"secondary component should not have template-only keys, but found: {leaked}"
    )
