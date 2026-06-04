from wizmodifier.apply import load_preset, run_preset
from wizmodifier.io import InputBundle


def test_preset_has_13_tests():
    preset = load_preset("import-test-matrix")
    assert [t["name"] for t in preset][:3] == ["T0-baseline", "T1-reserialized", "T2-new-speechid"]
    assert len(preset) == 13


def test_run_preset_writes_all_files(tmp_path, baseline_json_path):
    base = InputBundle.load(baseline_json_path)
    written = run_preset(base, "import-test-matrix", tmp_path, manifest_hash="t")
    names = sorted(p.name for p in written)
    assert "T0-baseline.zip" in names
    assert "T11-no-wav.zip" in names
    assert "T12-bare-json.json" in names
    assert (tmp_path / "results.md").exists()
