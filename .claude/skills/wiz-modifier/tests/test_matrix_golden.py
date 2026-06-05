import json
import zipfile
from pathlib import Path

from wizmodifier.apply import run_preset
from wizmodifier.io import InputBundle

GOLDEN = Path(__file__).parent / "golden" / "matrix_structure.json"


def _normalize(value):
    """Recursively zero out speechId and replace UUID-like values for stable diff."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k == "speechId":
                out[k] = 0
            elif k in ("componentUuid", "uuid", "value", "parentId") and isinstance(v, str):
                out[k] = "<uuid>" if v else ""
            else:
                out[k] = _normalize(v)
        return out
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _summary(bundle: InputBundle) -> dict:
    from wizmodifier import codec

    bsc = codec.decode(bundle.data["BizSpeechComponent"])
    details = bsc[0]["details"]
    return {
        "topkeys": len(bundle.data),
        "bsc_count": len(bsc),
        "bsc0_keys": sorted(bsc[0].keys()),
        "bsc0_details": _normalize(codec.decode(details)) if details != "null" else "null",
        "var_count": len(codec.decode(bundle.data["SpeechVariable"])),
        "intent_count": len(codec.decode(bundle.data["SpeechIntent"])),
    }


def test_matrix_structure_matches_golden(tmp_path, baseline_json_path):
    base = InputBundle.load(baseline_json_path)
    written = run_preset(base, "import-test-matrix", tmp_path, manifest_hash="fixed")
    actual = {}
    for p in written:
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                name = next(n for n in z.namelist() if n.endswith(".json"))
                data = json.loads(z.read(name))
        else:
            data = json.loads(p.read_text(encoding="utf-8"))
        actual[p.stem] = _summary(InputBundle(data=data, speech_name="s.json"))

    if not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(actual, indent=2, sort_keys=True), encoding="utf-8")
        raise AssertionError("golden created; re-run to verify")
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected
