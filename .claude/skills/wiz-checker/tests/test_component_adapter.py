from wizcheck.component_adapter import (
    is_component_export, component_export_to_full, BOT_SCOPE_CODES,
)

_COMP_EXPORT = {
    "name": "Main",
    "componentImportAndExportDTOS": [{
        "componentName": "Main",
        "componentUuid": "a227ff42-008d-4970-9eff-c43b3d18fd22",
        "speechComponentDTO": {
            "componentUuid": "a227ff42-008d-4970-9eff-c43b3d18fd22",
            "speechId": 1, "category": 1, "branch": "dev", "name": "Main",
            "sortIndex": 1, "parentUuid": "0", "updateTime": 123,
            "details": {}, "routes": {}, "inboundPorts": [],
        },
        "sentenceCutDTOList": [{
            "componentUuid": "a227ff42-008d-4970-9eff-c43b3d18fd22",
            "id": "0352c639-d634-4e06-a8b8-c0c5543f224e",
            "sen_rec_name": "", "sentence_text": "Halo?", "sentence_text_url": "",
            "sentenceCutId": 999, "speech_rec_cut_id": "08d59256-b044-5911-a401-c764ff28fa00",
            "showType": 0, "sortIndex": 1, "type": "record",
        }],
        "asrSceneEntityList": [],
    }],
    "speechIntentDTO": [
        {"intentId": 1, "intentName": "Unclassified", "isInit": 0, "language": "IDN",
         "keyWordInIntent": [], "userResponseInIntent": []},
    ],
    "speechVariableDTO": [
        {"beInit": 0, "id": 2, "name": "Customer Segment", "textType": "DEFAULT",
         "type": 0, "userId": 9, "variableSource": 1},
    ],
    "speechEntiEntityList": [], "speechEntityData": [],
    "speechFunctionDTO": [], "tagDTOList": [],
}

_FULL_EXPORT = {"BizSpeechComponent": [], "SpeechIntent": [], "SpeechVariable": []}


def test_is_component_export_true():
    assert is_component_export(_COMP_EXPORT) is True

def test_is_component_export_false_for_full():
    assert is_component_export(_FULL_EXPORT) is False

def test_bot_scope_codes():
    assert BOT_SCOPE_CODES == frozenset({"WIZ104", "WIZ110", "WIZ202", "WIZ303"})

def test_adapt_builds_required_top_level_keys():
    full = component_export_to_full(_COMP_EXPORT)
    for k in ("BizSpeechComponent", "SpeechVariable", "SpeechIntent",
              "SentenceCutSpeech", "SpeechAudio", "BizNodeHotWords"):
        assert k in full, f"missing required key {k}"
    assert full["SpeechAudio"] == []

def test_adapt_component_fields_and_decoded_details():
    full = component_export_to_full(_COMP_EXPORT)
    comp = full["BizSpeechComponent"][0]
    assert comp["componentUuid"] == "a227ff42-008d-4970-9eff-c43b3d18fd22"
    assert comp["createTime"]  # synthesized non-zero
    assert comp["updateTime"] == 123
    assert comp["details"] == {}          # decoded object, not a string
    assert isinstance(comp["details"], dict)

def test_adapt_sentence_cut_snake_to_camel():
    full = component_export_to_full(_COMP_EXPORT)
    row = full["SentenceCutSpeech"][0]
    assert row["sentenceText"] == "Halo?"
    assert row["senRecName"] == ""
    assert row["speechRecCutId"] == "08d59256-b044-5911-a401-c764ff28fa00"
    assert row["isDelete"] == 0
    assert row["id"] == "0352c639-d634-4e06-a8b8-c0c5543f224e"

def test_adapt_intent_and_variable():
    full = component_export_to_full(_COMP_EXPORT)
    intent = full["SpeechIntent"][0]
    assert intent["intentName"] == "Unclassified" and intent["isDelete"] == 0
    var = full["SpeechVariable"][0]
    assert var["name"] == "Customer Segment" and var["variableSource"] == 1

def test_adapt_empty_dto_lists_safe():
    minimal = {"componentImportAndExportDTOS": []}
    full = component_export_to_full(minimal)
    assert full["BizSpeechComponent"] == []
    assert "SpeechIntent" in full  # still present (empty)


from wizcheck.parser import parse_dict


def test_parse_dict_adapts_component_export():
    wf = parse_dict(_COMP_EXPORT)
    assert wf.is_component_export is True
    # raw is now the adapted full-shape dict
    assert "BizSpeechComponent" in wf.raw
    assert len(wf.components) == 1
    # flow model built from the adapted component
    assert wf.flow_model is not None


def test_parse_dict_full_export_flag_false():
    wf = parse_dict({"BizSpeechComponent": [], "SpeechIntent": [], "SpeechVariable": []})
    assert wf.is_component_export is False
