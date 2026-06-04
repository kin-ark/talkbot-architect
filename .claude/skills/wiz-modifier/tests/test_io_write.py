import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from wizmodifier.io import InputBundle, write_output


def _bundle():
    return InputBundle(
        data={"kbTag": "x"},
        speech_name="speech999.json",
        wavs={"a.wav": b"RIFF"},
    )


def test_write_json(tmp_path):
    out = tmp_path / "out.json"
    write_output(_bundle(), out, fmt="json")
    assert json.loads(out.read_text(encoding="utf-8")) == {"kbTag": "x"}


def test_write_zip_includes_wav(tmp_path):
    out = tmp_path / "out.zip"
    write_output(_bundle(), out, fmt="zip")
    with zipfile.ZipFile(out) as z:
        assert sorted(z.namelist()) == ["a.wav", "speech999.json"]
        assert z.read("a.wav") == b"RIFF"


def test_write_zip_no_wav(tmp_path):
    out = tmp_path / "out.zip"
    write_output(_bundle(), out, fmt="zip-no-wav")
    with zipfile.ZipFile(out) as z:
        assert z.namelist() == ["speech999.json"]
