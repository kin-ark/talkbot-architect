import io as _io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from wizmodifier.io import InputBundle


def test_load_bare_json(baseline_json_path):
    b = InputBundle.load(baseline_json_path)
    assert len(b.data) == 25
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
    try:
        InputBundle.load(zpath)
        assert False, "expected IOError"
    except IOError as e:
        assert "speech" in str(e).lower()
