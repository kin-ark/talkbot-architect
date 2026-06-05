import json
import zipfile

import pytest
from wizmodifier.io import InputBundle


def test_load_bare_json(baseline_json_path):
    b = InputBundle.load(baseline_json_path)
    # Empty+Dialogue baseline: 25 top-level keys
    # (see docs/original-vs-builder-deep-comparison.md §2)
    assert len(b.data) == 25
    assert "BizSpeechComponent" in b.data
    assert b.speech_name == baseline_json_path.name
    assert b.wavs == {}


def test_load_zip_with_wav(tmp_path):
    zpath = tmp_path / "bot.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("speech123.json", json.dumps({"kbTag": "x"}))
        z.writestr("audio1.wav", b"RIFFfake")
    b = InputBundle.load(zpath)
    assert b.speech_name == "speech123.json"
    assert b.wavs == {"audio1.wav": b"RIFFfake"}
    assert b.data == {"kbTag": "x"}


def test_load_zip_requires_one_speech_json(tmp_path):
    zpath = tmp_path / "bad.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("notspeech.txt", "x")
    with pytest.raises(ValueError, match="speech"):
        InputBundle.load(zpath)
