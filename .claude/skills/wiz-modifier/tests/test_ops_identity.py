import sys
from pathlib import Path

# wiz-builder's scripts dir is a sibling skill, not on pythonpath.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "wiz-builder" / "scripts")
)

from wizbuilder.ids import IdMinter  # noqa: E402
from wizmodifier import codec  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops import identity  # noqa: E402
from wizmodifier.ops._bsc import get_components  # noqa: E402

MINTER = IdMinter(manifest_hash="deadbeef")


def test_set_speech_id_explicit_walks_all_fields(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    identity.set_speech_id(b, {"value": 1234567890123456}, MINTER)
    comps = get_components(b)
    assert comps[0]["speechId"] == 1234567890123456
    # SpeechVariable carries speechId too — confirm the walk reached it.
    sv = codec.decode(b.data["SpeechVariable"])
    assert all(v["speechId"] == 1234567890123456 for v in sv)


def test_set_speech_id_random_is_16_digits(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    identity.set_speech_id(b, {"value": "random"}, MINTER)
    sid = get_components(b)[0]["speechId"]
    assert 10**15 <= sid < 10**16


def test_set_bsc_name(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    identity.set_bsc_name(b, {"component": 0, "value": "1. Greeting"}, MINTER)
    assert get_components(b)[0]["name"] == "1. Greeting"


def test_set_bsc_id(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    identity.set_bsc_id(b, {"component": 0, "value": 42}, MINTER)
    assert get_components(b)[0]["id"] == 42


def test_set_component_uuid_explicit(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    identity.set_component_uuid(b, {"component": 0, "value": "abc-123"}, MINTER)
    assert get_components(b)[0]["componentUuid"] == "abc-123"
