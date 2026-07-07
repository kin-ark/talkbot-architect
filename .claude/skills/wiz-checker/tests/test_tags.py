import json

from wizcheck.parser import parse_dict


def _bot_with_tags():
    speech_tag = [
        {"id": 100, "name": "Debt Result", "isMutex": 1, "type": 0, "tagProperty": 0,
         "bizTagPropertyDTOS": [
             {"id": 101, "tagId": 100, "value": "Refuse Payment"},
             {"id": 102, "tagId": 100, "value": "Willing to Repay"}]},
        {"id": 200, "name": "Payment Method", "isMutex": 0, "type": 3, "tagProperty": 0,
         "bizTagPropertyDTOS": [{"id": 201, "tagId": 200, "value": ""}]},
    ]
    return {
        "SpeechTag": json.dumps(speech_tag),
        "SpeechVariable": "[]", "SpeechIntent": "[]", "SentenceCutSpeech": "[]",
        "SpeechAudio": "[]", "BizSpeechComponent": "[]", "BizKnowledgeInfo": "[]",
    }


def test_parse_speech_tag_into_ir():
    wf = parse_dict(_bot_with_tags())
    assert len(wf.tags) == 2
    cat = {c.id: c for c in wf.tags}
    assert set(cat) == {"100", "200"}
    debt = cat["100"]
    assert debt.name == "Debt Result"
    assert debt.is_mutex == 1
    assert debt.type == 0
    assert {v.id for v in debt.values} == {"101", "102"}
    v = next(v for v in debt.values if v.id == "101")
    assert v.value == "Refuse Payment"
    assert v.tag_id == "100"


def test_parse_empty_speech_tag():
    raw = _bot_with_tags()
    raw["SpeechTag"] = "[]"
    wf = parse_dict(raw)
    assert wf.tags == ()


def test_parse_missing_speech_tag():
    raw = _bot_with_tags()
    del raw["SpeechTag"]
    wf = parse_dict(raw)
    assert wf.tags == ()
