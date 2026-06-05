import json
import zipfile

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


def test_run_preset_is_cumulative(tmp_path, baseline_json_path):
    """T8's output must retain T7's populate-details mutation AND add a 2nd
    component — proving transformations compose (the point of the bisect matrix)."""
    base = InputBundle.load(baseline_json_path)
    run_preset(base, "import-test-matrix", tmp_path, manifest_hash="t")
    with zipfile.ZipFile(tmp_path / "T8-multi-component.zip") as z:
        name = next(n for n in z.namelist() if n.endswith(".json"))
        data = json.loads(z.read(name))
    comps = json.loads(data["BizSpeechComponent"])
    assert len(comps) == 2  # T8 added a second component
    assert comps[0]["details"] != "null"  # T7's populate-details survived into T8
