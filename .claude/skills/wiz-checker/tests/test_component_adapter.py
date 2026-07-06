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


from wizcheck.component_adapter import full_to_component_export

# A full-export-shaped dict as the BUILDER emits it: top-level sections are
# escaped-JSON STRINGS; per-component details/routes are strings too;
# intents carry bracket-string keyword fields.
import json as _json
_FULL = {
    "BizSpeechComponent": _json.dumps([{
        "componentUuid": "c-1", "name": "Main", "branch": "dev", "category": 1,
        "speechId": 7, "templateCode": "T", "type": 1, "editStatus": 2, "useStatus": 1,
        "parentUuid": "0", "sortIndex": 1, "createTime": 100, "updateTime": 200,
        "createBy": "x", "language": "IDN", "id": 55,
        "details": _json.dumps({"n1": {"type": 1, "data": {"type": 1, "list": ["hi"]}}}),
        "routes": _json.dumps({"n1": {}}),
        "inboundPorts": _json.dumps([{"uuid": "n1"}]),
        "outboundPorts": "[]", "topFloorDetails": "[]", "nluConf": "{}", "sourceUuid": "",
    }]),
    "SentenceCutSpeech": _json.dumps([{
        "id": "n1", "componentUuid": "c-1", "sentenceText": "hi", "senRecName": "",
        "sentenceTextUrl": "", "speechRecCutId": "r1", "sentenceCutId": 999,
        "showType": 0, "sortIndex": 1, "type": "record", "isDelete": 0,
        "branch": "dev", "speechId": 7,
    }]),
    "SpeechIntent": _json.dumps([{
        "intentId": 1, "intentName": "Positive", "isInit": 1, "language": "IDN",
        "keyWordInIntent": "[Ya,Betul]", "userResponseInIntent": "[]",
        "branch": "dev", "isDelete": 0, "nodeId": "", "speechId": 7,
        "templateCode": "T", "createTime": 0, "updateTime": 0,
    }]),
    "SpeechVariable": _json.dumps([{
        "id": 2, "name": "Segment", "textType": "DEFAULT", "type": 1,
        "userId": 9, "variableSource": 0, "beInit": 0, "branch": "dev",
        "createTime": 0, "enumVariable": 0, "speechId": 7, "templateCode": "T",
    }]),
    "SpeechAudio": "[]", "BizNodeHotWords": "[]",
}


def test_full_to_component_export_envelope_shape():
    dto = full_to_component_export(_FULL, name="Main")
    assert dto["name"] == "Main"
    for k in ("componentImportAndExportDTOS", "speechIntentDTO", "speechVariableDTO",
              "speechEntiEntityList", "speechEntityData", "speechFunctionDTO", "tagDTOList"):
        assert k in dto
    assert dto["speechEntiEntityList"] == [] and dto["speechFunctionDTO"] == []


def test_full_to_component_export_component_decoded():
    dto = full_to_component_export(_FULL)
    entry = dto["componentImportAndExportDTOS"][0]
    assert entry["componentName"] == "Main" and entry["componentUuid"] == "c-1"
    scd = entry["speechComponentDTO"]
    assert isinstance(scd["details"], dict)        # decoded, not a string
    assert isinstance(scd["routes"], dict)
    assert isinstance(scd["inboundPorts"], list)
    assert "createTime" not in scd and "language" not in scd  # dropped
    assert scd["version"] == "4"


def test_full_to_component_export_sentence_cut_snake():
    dto = full_to_component_export(_FULL)
    row = dto["componentImportAndExportDTOS"][0]["sentenceCutDTOList"][0]
    assert row["sentence_text"] == "hi" and row["speech_rec_cut_id"] == "r1"
    assert "sentenceText" not in row and "branch" not in row and "speechId" not in row


def test_full_to_component_export_intent_arrays():
    dto = full_to_component_export(_FULL)
    intent = dto["speechIntentDTO"][0]
    assert intent["keyWordInIntent"] == ["Ya", "Betul"]      # bracket-string -> array
    assert intent["userResponseInIntent"] == []
    assert intent["preExclusiveKeyword"] == [] and "branch" not in intent


def test_full_to_component_export_variable_trim():
    dto = full_to_component_export(_FULL)
    var = dto["speechVariableDTO"][0]
    assert var["name"] == "Segment" and var["variableSource"] == 0
    assert "branch" not in var and "enumVariable" not in var


def test_roundtrip_dto_to_full_to_dto():
    # Start from a component export, go full, come back — key structure preserved.
    dto0 = _COMP_EXPORT  # the fixture already defined earlier in this test module
    full = component_export_to_full(dto0)
    # re-encode the top-level sections as the builder would (strings), so
    # full_to_component_export sees builder-shaped input:
    import json
    full_str = {k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                for k, v in full.items()}
    dto1 = full_to_component_export(full_str, name=dto0.get("name"))
    e0 = dto0["componentImportAndExportDTOS"][0]
    e1 = dto1["componentImportAndExportDTOS"][0]
    assert e1["componentUuid"] == e0["componentUuid"]
    assert e1["speechComponentDTO"]["name"] == e0["speechComponentDTO"]["name"]
