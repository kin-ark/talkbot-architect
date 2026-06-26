import json
import speechname


def _packed(scene: dict) -> dict:
    return {"BizSpeechComponent": [], "BizSpeechScene": json.dumps(scene, ensure_ascii=False)}


def test_read_packed_string_scene():
    data = _packed({"speechName": "Empty Dialogue", "speechId": 8309})
    assert speechname.read_speech_name(data) == "Empty Dialogue"


def test_read_unpacked_dict_scene():
    data = {"BizSpeechScene": {"speechName": "Debt Collector"}}
    assert speechname.read_speech_name(data) == "Debt Collector"


def test_read_missing_scene_is_none():
    assert speechname.read_speech_name({"BizSpeechComponent": []}) is None
    assert speechname.read_speech_name({"BizSpeechScene": {"speechName": ""}}) is None


def test_set_packed_preserves_string_form_and_other_keys():
    data = _packed({"speechName": "Empty Dialogue", "speechId": 8309})
    out = speechname.set_speech_name(data, "Debt Collector")
    assert isinstance(out["BizSpeechScene"], str)            # stayed a JSON string
    scene = json.loads(out["BizSpeechScene"])
    assert scene["speechName"] == "Debt Collector"
    assert scene["speechId"] == 8309                          # untouched
    assert speechname.read_speech_name(data) == "Empty Dialogue"  # input not mutated


def test_set_unpacked_preserves_dict_form():
    data = {"BizSpeechScene": {"speechName": "old", "speechId": 1}}
    out = speechname.set_speech_name(data, "new")
    assert isinstance(out["BizSpeechScene"], dict)
    assert out["BizSpeechScene"]["speechName"] == "new"


def test_set_missing_scene_is_noop():
    data = {"BizSpeechComponent": []}
    out = speechname.set_speech_name(data, "X")
    assert out == {"BizSpeechComponent": []}


def test_slugify():
    assert speechname.slugify_filename("Debt Collector") == "Debt_Collector.json"
    assert speechname.slugify_filename("  A/B:c!  ") == "ABc.json"
    assert speechname.slugify_filename("") == "speech_export.json"
    assert speechname.slugify_filename("已经") == "speech_export.json"  # non-ascii stripped -> fallback
