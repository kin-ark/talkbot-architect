import json

import pytest

from wizmodifier.io import InputBundle
from wizmodifier.apply import run_mods
from wizmodifier.xlsx import write_sheet


def _bundle(extra_kb=False):
    # SpeechIntent with "Benefit" present; a baseline BizKnowledgeInfo entry to clone constants.
    si = [{"branch": "dev", "createTime": 0, "intentId": 100, "intentName": "Benefit",
           "isDelete": 0, "isInit": 1, "keyWordInIntent": "[x]", "language": "IDN",
           "nodeId": "", "speechId": 9, "templateCode": "T", "updateTime": 0,
           "userResponseInIntent": "[]"}]
    base_kb = {
        "kdTitle": "Existing KB", "knowledgeId": 5, "speechId": 9, "createId": 0,
        "createTime": 0, "modifyId": 0, "modifyTime": 0, "branch": "dev",
        "isInit": 0, "isDelete": 0, "exclusiveKeyWords": "[]",
        "intents": json.dumps([{"intentName": "Benefit", "intentId": 100}]),
        "kdInfo": json.dumps([{"answerType": 1, "answer": "old answer",
                               "editorValue": {"text": "old answer"}, "id": "a1"}]),
        "conditions": "null", "answerType": 1,
    }
    return InputBundle(data={
        "SpeechIntent": json.dumps(si), "SpeechVariable": "[]",
        "BizSpeechComponent": "[]", "SentenceCutSpeech": "[]",
        "SentenceCutKnowledge": "[]",
        "BizKnowledgeInfo": json.dumps([base_kb]), "kbTag": [],
    }, speech_name="speech1.json")


def _kbs(bundle):
    return {k["kdTitle"]: k for k in json.loads(bundle.data["BizKnowledgeInfo"])}


def _answers(kb):
    return [it.get("answer") for it in json.loads(kb["kdInfo"]) if it.get("answerType") == 1]


def _sheet(tmp_path, rows):
    p = tmp_path / "kb.xls"
    write_sheet(p, ["Title", "Intent", "Dialogue Content"], rows, note="Note: kb")
    return p


def test_import_adds_new_kb(tmp_path):
    p = _sheet(tmp_path, [["KB Benefit", "Benefit", "[Allianz covers you.]"]])
    b = _bundle()
    run_mods(b, [{"op": "import-kb-xlsx", "path": str(p)}], manifest_hash="h")
    kbs = _kbs(b)
    assert "KB Benefit" in kbs
    kb = kbs["KB Benefit"]
    assert _answers(kb) == ["Allianz covers you."]        # brackets stripped
    assert json.loads(kb["intents"])[0]["intentName"] == "Benefit"


def test_import_missing_intent_warns_and_skips(tmp_path):
    p = _sheet(tmp_path, [
        ["KB Benefit", "Benefit", "[ok]"],
        ["KB Ghost", "NoSuchIntent", "[nope]"],
    ])
    b = _bundle()
    run_mods(b, [{"op": "import-kb-xlsx", "path": str(p)}], manifest_hash="h")
    kbs = _kbs(b)
    assert "KB Benefit" in kbs and "KB Ghost" not in kbs
    assert any("NoSuchIntent" in w or "KB Ghost" in w for w in b.warnings)


def test_import_updates_existing_kb(tmp_path):
    p = _sheet(tmp_path, [["Existing KB", "Benefit", "[new answer]"]])
    b = _bundle()
    run_mods(b, [{"op": "import-kb-xlsx", "path": str(p)}], manifest_hash="h")
    kbs = _kbs(b)
    # not duplicated; first answer replaced
    assert sum(1 for k in json.loads(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Existing KB") == 1
    assert "new answer" in _answers(kbs["Existing KB"])
    assert "old answer" not in _answers(kbs["Existing KB"])


def test_import_duplicate_title_skips_second(tmp_path):
    p = _sheet(tmp_path, [
        ["Dup", "Benefit", "[first]"],
        ["Dup", "Benefit", "[second]"],
    ])
    b = _bundle()
    run_mods(b, [{"op": "import-kb-xlsx", "path": str(p)}], manifest_hash="h")
    assert sum(1 for k in json.loads(b.data["BizKnowledgeInfo"]) if k["kdTitle"] == "Dup") == 1
    assert any("Dup" in w for w in b.warnings)


def test_import_strip_brackets_and_plain(tmp_path):
    from wizmodifier.ops.kb_xlsx import _strip_brackets
    assert _strip_brackets("[hello]") == "hello"
    assert _strip_brackets("hello") == "hello"
    assert _strip_brackets("[a,b]") == "a,b"   # commas are answer text, not split


def test_import_missing_column_raises(tmp_path):
    p = tmp_path / "bad.xls"
    write_sheet(p, ["Title", "Intent"], [["A", "Benefit"]])  # no Dialogue Content
    b = _bundle()
    with pytest.raises(ValueError):
        run_mods(b, [{"op": "import-kb-xlsx", "path": str(p)}], manifest_hash="h")


def test_import_component_mode_rejected(tmp_path):
    p = _sheet(tmp_path, [["KB Benefit", "Benefit", "[ok]"]])
    b = _bundle(); b.is_component = True
    with pytest.raises(ValueError, match="component mode"):
        run_mods(b, [{"op": "import-kb-xlsx", "path": str(p)}], manifest_hash="h")
