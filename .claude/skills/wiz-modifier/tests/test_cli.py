import subprocess
import sys
import zipfile
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "scripts" / "modify.py"
ROOT = Path(__file__).resolve().parents[4]
BASELINE = ROOT / "talkbot" / "Empty+Dialogue" / "speech4010869963530658988.json"
BASELINE_ZIP = ROOT / "talkbot" / "Empty+Dialogue.zip"


def _run(args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_preset_run_creates_matrix(tmp_path):
    r = _run(["--preset", "import-test-matrix", "--in", str(BASELINE),
              "--out", str(tmp_path), "--force", "--no-check"])
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "T0-baseline.zip").exists()
    assert (tmp_path / "results.md").exists()


def test_preset_from_zip_carries_wav(tmp_path):
    r = _run(["--preset", "import-test-matrix", "--in", str(BASELINE_ZIP),
              "--out", str(tmp_path), "--force", "--no-check"])
    assert r.returncode == 0, r.stderr
    with zipfile.ZipFile(tmp_path / "T0-baseline.zip") as z:
        assert any(n.endswith(".wav") for n in z.namelist())
    with zipfile.ZipFile(tmp_path / "T11-no-wav.zip") as z:
        assert not any(n.endswith(".wav") for n in z.namelist())


def test_mods_run_writes_zip(tmp_path):
    mods = tmp_path / "m.yaml"
    out = tmp_path / "out.zip"
    mods.write_text(
        f"input: {BASELINE.as_posix()}\n"
        f"wav: {(BASELINE.parent / '01735200078309635328.wav').as_posix()}\n"
        "mods:\n  - op: set-bsc-name\n    component: 0\n    value: Hi\n"
        f"output:\n  path: {out.as_posix()}\n  format: zip\n",
        encoding="utf-8",
    )
    r = _run(["--mods", str(mods), "--force", "--no-check"])
    assert r.returncode == 0, r.stderr
    with zipfile.ZipFile(out) as z:
        assert any(n.endswith(".wav") for n in z.namelist())


def test_path_conflict_without_force(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("existing", encoding="utf-8")
    mods = tmp_path / "m.yaml"
    mods.write_text(
        f"input: {BASELINE.as_posix()}\nmods: []\n"
        f"output:\n  path: {out.as_posix()}\n  format: json\n",
        encoding="utf-8",
    )
    r = _run(["--mods", str(mods), "--no-check"])
    assert r.returncode == 3


def test_unknown_op_exits_2(tmp_path):
    mods = tmp_path / "m.yaml"
    mods.write_text(
        f"input: {BASELINE.as_posix()}\n"
        "mods:\n  - op: frobnicate\n"
        f"output:\n  path: {(tmp_path / 'x.json').as_posix()}\n  format: json\n",
        encoding="utf-8",
    )
    r = _run(["--mods", str(mods), "--no-check"])
    assert r.returncode == 2
    assert "frobnicate" in r.stderr
