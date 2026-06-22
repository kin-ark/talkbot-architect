import json
from pathlib import Path
import agents

_REAL = Path(__file__).resolve().parents[3] / "speech2572824560161596380.unpacked.json"
_DATA = json.loads(_REAL.read_text(encoding="utf-8"))


def test_propose_set_speech_id_changes_data():
    res = agents.propose_mods(_DATA, "- op: set-speech-id\n  value: 123456\n")
    assert res["ok"] is True
    assert res["proposed_data"] is not _DATA
    assert res["diff"]  # non-empty


def test_propose_unknown_op_returns_error():
    res = agents.propose_mods(_DATA, "- op: not-a-real-op\n")
    assert res["ok"] is False
    assert "not-a-real-op" in res["error"]
