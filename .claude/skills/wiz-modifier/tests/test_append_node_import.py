import json
import subprocess
import sys
from pathlib import Path
from wizmodifier.io import InputBundle
from wizmodifier.apply import run_mods

ROOT = Path(__file__).resolve().parents[4]
BASELINE = ROOT / "talkbot" / "Empty+Dialogue.zip"
CHECK = ROOT / ".claude" / "skills" / "wiz-checker" / "scripts" / "check.py"


def _comp0_details(bundle):
    raw = bundle.data["BizSpeechComponent"]
    comps = json.loads(raw) if isinstance(raw, str) else raw
    d = comps[0].get("details")
    return json.loads(d) if isinstance(d, str) and d not in ("null", "") else {}


def test_append_result_is_checker_clean(tmp_path):
    b = InputBundle.load(BASELINE)

    # Op 1: add the entry node "g"
    run_mods(b, [
        {"op": "append-node", "component": 0, "node": {"id": "g", "prompt": "Greeting"}},
    ], manifest_hash="imp")

    # Read the uuid that was just minted for "g" (only uuid in details after first op)
    g_uuid = next(iter(_comp0_details(b).keys()))

    # Op 2: add a closing node "c", wired from g via its uuid (logical id "g" is gone)
    run_mods(b, [
        {"op": "append-node", "component": 0,
         "node": {"id": "c", "prompt": "Closing"},
         "edges": [{"from": g_uuid, "branch": "Unclassified", "to": "c"}]},
    ], manifest_hash="imp")

    out = tmp_path / "appended.json"
    out.write_text(json.dumps(b.data, ensure_ascii=False), encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(CHECK), str(out)],
        capture_output=True, text=True,
    )
    # check.py exits 0 when no errors. Surface output on failure.
    assert res.returncode == 0, res.stdout + res.stderr
