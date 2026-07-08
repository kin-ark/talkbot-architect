from pathlib import Path

import pytest

from wizmodifier.xlsx import read_rows, write_sheet


def test_write_then_read_roundtrip(tmp_path):
    # write to an .xls-named path (WIZ's quirk: xlsx bytes, .xls extension)
    p = tmp_path / "out.xls"
    write_sheet(p, ["Intent", "Type", "Content", "Language"],
                [["Positive", "Keyword", "ya", "Bahasa Indonesia"]],
                note="Note: test")
    rows = read_rows(p)
    # note row, header row, data row
    assert rows[0][0].startswith("Note")
    assert rows[1] == ["Intent", "Type", "Content", "Language"]
    assert rows[2] == ["Positive", "Keyword", "ya", "Bahasa Indonesia"]


def test_read_bytesio_bypasses_xls_extension(tmp_path):
    # write_sheet writes real xlsx bytes; naming it .xls must still read (BytesIO).
    p = tmp_path / "sheet.xls"
    write_sheet(p, ["A"], [["x"]])
    rows = read_rows(p)
    assert rows[-1] == ["x"]


def test_read_missing_file_raises(tmp_path):
    with pytest.raises(ValueError):
        read_rows(tmp_path / "nope.xls")


import json

from wizmodifier.io import InputBundle
from wizmodifier.apply import run_mods
from wizmodifier.xlsx import write_sheet


def _bundle():
    # baseline with one existing intent "Positive" + defaults the ops need
    si = [{"branch": "dev", "createTime": 0, "intentId": 1, "intentName": "Positive",
           "isDelete": 0, "isInit": 1, "keyWordInIntent": "[]", "language": "IDN",
           "nodeId": "", "speechId": 9, "templateCode": "T", "updateTime": 0,
           "userResponseInIntent": "[]"}]
    return InputBundle(data={
        "SpeechIntent": json.dumps(si), "SpeechVariable": "[]",
        "BizSpeechComponent": "[]", "SentenceCutSpeech": "[]",
        "BizKnowledgeInfo": "[]", "kbTag": [],
    }, speech_name="speech1.json")


def _intents(bundle):
    return {i["intentName"]: i for i in json.loads(bundle.data["SpeechIntent"])}


def _sheet(tmp_path, rows):
    p = tmp_path / "intents.xls"
    write_sheet(p, ["Intent", "Type", "Content", "Language"], rows, note="Note: x")
    return p


def test_import_adds_new_and_updates_existing(tmp_path):
    p = _sheet(tmp_path, [
        ["Positive", "Keyword", "ya", "Bahasa Indonesia"],
        ["Positive", "User response", "ya boleh", "Bahasa Indonesia"],
        ["Will pay", "Keyword", "bayar", "English"],
        ["Will pay", "User response", "saya akan bayar", "English"],
    ])
    b = _bundle()
    run_mods(b, [{"op": "import-intents-xlsx", "path": str(p)}], manifest_hash="h")
    it = _intents(b)
    assert "Will pay" in it and it["Will pay"]["isInit"] == 1
    assert it["Will pay"]["language"] == "ENG"
    assert it["Will pay"]["keyWordInIntent"] == "[bayar]"
    assert it["Will pay"]["userResponseInIntent"] == "[saya akan bayar]"
    # existing Positive updated in place (not duplicated)
    assert it["Positive"]["keyWordInIntent"] == "[ya]"
    assert sum(1 for i in json.loads(b.data["SpeechIntent"]) if i["intentName"] == "Positive") == 1


def test_import_warns_and_skips_include_exclude(tmp_path):
    p = _sheet(tmp_path, [
        ["Will pay", "Keyword", "bayar", "English"],
        ["Will pay", "Include", "must", "English"],
        ["Will pay", "Exclude", "not", "English"],
    ])
    b = _bundle()
    run_mods(b, [{"op": "import-intents-xlsx", "path": str(p)}], manifest_hash="h")
    it = _intents(b)
    assert it["Will pay"]["keyWordInIntent"] == "[bayar]"  # Keyword applied
    assert any("Include" in w or "Exclude" in w or "advanced" in w.lower() for w in b.warnings)


def test_import_unknown_language_warns_defaults_idn(tmp_path):
    p = _sheet(tmp_path, [["Foo", "Keyword", "x", "Malaysia"]])
    b = _bundle()
    run_mods(b, [{"op": "import-intents-xlsx", "path": str(p)}], manifest_hash="h")
    assert _intents(b)["Foo"]["language"] == "IDN"
    assert any("Malaysia" in w or "language" in w.lower() for w in b.warnings)


def test_import_missing_columns_raises(tmp_path):
    p = tmp_path / "bad.xls"
    write_sheet(p, ["Intent", "Content"], [["A", "x"]])  # no Type column
    b = _bundle()
    with pytest.raises(ValueError):
        run_mods(b, [{"op": "import-intents-xlsx", "path": str(p)}], manifest_hash="h")


def test_import_component_mode_rejected(tmp_path):
    p = _sheet(tmp_path, [["Foo", "Keyword", "x", "English"]])
    b = _bundle(); b.is_component = True
    with pytest.raises(ValueError, match="component mode"):
        run_mods(b, [{"op": "import-intents-xlsx", "path": str(p)}], manifest_hash="h")
