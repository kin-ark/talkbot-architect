import pytest
from wizmodifier.mods import ModManifest, ModManifestError, load_mods


def test_load_valid(tmp_path):
    text = """
input: talkbot/Empty+Dialogue/speech4010869963530658988.json
mods:
  - op: set-speech-id
    value: random
output:
  path: out/x.zip
  format: zip
"""
    p = tmp_path / "m.yaml"
    p.write_text(text, encoding="utf-8")
    m = load_mods(p)
    assert isinstance(m, ModManifest)
    assert m.input.endswith("speech4010869963530658988.json")
    assert m.mods[0]["op"] == "set-speech-id"
    assert m.output_format == "zip"


def test_unknown_op_rejected(tmp_path):
    text = """
input: a.json
mods:
  - op: frobnicate
output:
  path: out/x.json
  format: json
"""
    p = tmp_path / "m.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ModManifestError, match="frobnicate"):
        load_mods(p)


def test_bad_format_rejected(tmp_path):
    text = """
input: a.json
mods: []
output:
  path: out/x.json
  format: tarball
"""
    p = tmp_path / "m.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ModManifestError):
        load_mods(p)
