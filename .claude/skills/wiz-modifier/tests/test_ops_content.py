import sys
from pathlib import Path

# wiz-builder's scripts dir is a sibling skill, not on pythonpath.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "wiz-builder" / "scripts")
)

from wizbuilder.ids import IdMinter  # noqa: E402
from wizmodifier import codec  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops import content  # noqa: E402

MINTER = IdMinter(manifest_hash="deadbeef")


def test_add_variable_appends_12_key_shape(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    before = len(codec.decode(b.data["SpeechVariable"]))
    content.add_variable(b, {"name": "user_name", "branch": "dev"}, MINTER)
    sv = codec.decode(b.data["SpeechVariable"])
    assert len(sv) == before + 1
    added = sv[-1]
    assert added["name"] == "user_name"
    assert added["type"] == 1
    assert added["variableSource"] == 0
    assert set(added.keys()) == {
        "beInit", "branch", "createTime", "enumVariable", "id", "name",
        "speechId", "templateCode", "textType", "type", "userId", "variableSource",
    }


def test_add_intent_appends_13_key_shape(baseline_dict):
    b = InputBundle(data=baseline_dict, speech_name="s.json")
    before = len(codec.decode(b.data["SpeechIntent"]))
    content.add_intent(
        b,
        {"name": "yes", "branch": "dev", "language": 0,
         "keywords": ["ya", "betul"], "user_responses": ["Ya"]},
        MINTER,
    )
    si = codec.decode(b.data["SpeechIntent"])
    assert len(si) == before + 1
    added = si[-1]
    assert added["intentName"] == "yes"
    assert added["keyWordInIntent"] == "[ya,betul]"
    assert added["userResponseInIntent"] == "[Ya]"
