import sys
from pathlib import Path

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
        "nluConf": "{}", "sourceUuid": "", "topFloorDetails": "{}",
    }.items():
        assert comp[k] == v


def test_populate_details_builds_envelope(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    structure.populate_details(
        b,
        {"component": 0, "nodes": [{"id": "n1", "label": "Greeting", "parent": None}]},
        MINTER,
    )
    comp = get_components(b)[0]
    details = codec.decode(comp["details"])
    envelope = next(iter(details.values()))
    nodes = envelope["canvas"]["component"]["props"]["list"]
    assert nodes[0]["label"] == "Greeting"
    assert nodes[0]["parentId"] == ""
    assert nodes[0]["uuid"] == nodes[0]["value"]


def test_add_component_appends_entry(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    before = len(get_components(b))
    structure.add_component(b, {"name": "Second Canvas"}, MINTER)
    comps = get_components(b)
    assert len(comps) == before + 1
    assert comps[-1]["name"] == "Second Canvas"
    assert comps[-1]["details"] == "null"  # no nodes given
