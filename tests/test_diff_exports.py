import json
import sys
import zipfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from diff_exports import decode_field, diff_exports, load_export, normalize_speech_ids


def test_load_export_json(tmp_path):
    data = {"BizSpeechComponent": "[]", "kbTag": "0"}
    p = tmp_path / "speech123.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert load_export(p) == data


def test_load_export_zip(tmp_path):
    data = {"BizSpeechComponent": "[]"}
    zp = tmp_path / "export.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("speech999.json", json.dumps(data))
    assert load_export(zp) == data


def test_load_export_zip_requires_one_speech_json(tmp_path):
    zp = tmp_path / "bad.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("other.json", "{}")
    with pytest.raises(ValueError, match="expected 1 speech"):
        load_export(zp)


def test_normalize_speech_ids_nested():
    obj = {"speechId": 99, "child": {"speechId": 42, "name": "keep"}}
    result = normalize_speech_ids(obj)
    assert result["speechId"] == 0
    assert result["child"]["speechId"] == 0
    assert result["child"]["name"] == "keep"


def test_normalize_speech_ids_in_list():
    obj = [{"speechId": 1}, {"speechId": 2, "other": "x"}]
    result = normalize_speech_ids(obj)
    assert result[0]["speechId"] == 0
    assert result[1]["other"] == "x"


def test_decode_field_json_string():
    assert decode_field('[{"id": 1}]') == [{"id": 1}]


def test_decode_field_non_json_passthrough():
    assert decode_field("not valid {json") == "not valid {json"


def test_decode_field_non_string_passthrough():
    assert decode_field(42) == 42


def test_diff_exports_detects_count_mismatch(capsys):
    a = {"BizSpeechComponent": json.dumps([{"id": 1}, {"id": 2}])}
    b = {"BizSpeechComponent": json.dumps([{"id": 1}])}
    diff_exports(a, b)
    out = capsys.readouterr().out
    assert "MISMATCH" in out
    assert "BizSpeechComponent" in out


def test_diff_exports_no_mismatch_on_equal(capsys):
    a = {"BizSpeechComponent": json.dumps([{"id": 1}])}
    b = {"BizSpeechComponent": json.dumps([{"id": 1}])}
    diff_exports(a, b)
    out = capsys.readouterr().out
    assert "MISMATCH" not in out


def test_diff_exports_detects_key_gap(capsys):
    a = {"SpeechVariable": json.dumps([{"id": 1, "extra": "x"}])}
    b = {"SpeechVariable": json.dumps([{"id": 1}])}
    diff_exports(a, b)
    out = capsys.readouterr().out
    assert "extra" in out


def test_diff_exports_focus_filters_fields(capsys):
    a = {"FieldA": json.dumps([{"id": 1}, {"id": 2}]), "FieldB": json.dumps([{"id": 1}])}
    b = {"FieldA": json.dumps([{"id": 1}]), "FieldB": json.dumps([{"id": 1}])}
    diff_exports(a, b, focus=["FieldB"])
    out = capsys.readouterr().out
    assert "FieldA" not in out
    assert "FieldB" in out
