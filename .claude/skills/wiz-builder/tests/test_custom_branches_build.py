import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from wizbuilder.compile import compile_manifest
from wizbuilder.manifest import ManifestError, load_manifest

_BUILDER = Path(__file__).resolve().parents[1]
_SKILLS = _BUILDER.parent
_CHECK = _SKILLS / "wiz-checker" / "scripts" / "check.py"


def _manifest(tmp_path, **over):
    m = {
        "name": "CustomBranchBot", "language": "IDN", "branch": "dev",
        "custom_intents": [
            {"name": "PaidCash", "language": "IDN", "keywords": ["sudah bayar tunai"]},
            {"name": "PaidTransfer", "language": "IDN", "keywords": ["sudah transfer"]},
        ],
        "canvases": [{
            "name": "Main",
            "nodes": [
                {"id": "ask", "type": "talk", "prompt": "Sudah bayar?",
                 "config": {"branch_intents": {"Paid": ["PaidCash", "PaidTransfer"]}}},
                {"id": "thanks", "type": "talk", "prompt": "Terima kasih"},
                {"id": "retry", "type": "talk", "prompt": "Mohon diselesaikan"},
                {"id": "bye", "type": "exit", "prompt": "Sampai jumpa"},
            ],
            "edges": [
                {"from": "ask", "branch": "Paid", "to": "thanks"},
                {"from": "ask", "branch": "Unclassified", "to": "retry"},
                {"from": "thanks", "branch": "Unclassified", "to": "bye"},
                {"from": "retry", "branch": "Unclassified", "to": "bye"},
            ],
        }],
    }
    m.update(over)
    p = tmp_path / "m.yaml"
    p.write_text(yaml.safe_dump(m), encoding="utf-8")
    return p


def test_custom_branch_compiles_checker_clean(tmp_path):
    out = tmp_path / "out.json"
    compile_manifest(str(_manifest(tmp_path)), str(out))   # raises if checker errors
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["BizSpeechComponent"]
    res = subprocess.run([sys.executable, str(_CHECK), str(out), "--json"],
                         capture_output=True, text=True)
    if not res.stdout:
        raise AssertionError(f"Checker produced no output. stderr: {res.stderr}")
    findings = json.loads(res.stdout)
    assert not [f for f in findings["findings"] if f["severity"] == "error"]


def test_undeclared_intent_raises(tmp_path):
    p = _manifest(tmp_path,
                  custom_intents=[{"name": "PaidCash", "language": "IDN", "keywords": ["x"]}])
    with pytest.raises(ManifestError, match="not a declared custom_intent"):
        load_manifest(str(p))


def test_custom_branch_without_unclassified_raises(tmp_path):
    m = yaml.safe_load(_manifest(tmp_path).read_text(encoding="utf-8"))
    m["canvases"][0]["edges"] = [e for e in m["canvases"][0]["edges"]
                                 if not (e["from"] == "ask" and e["branch"] == "Unclassified")]
    p = tmp_path / "m2.yaml"
    p.write_text(yaml.safe_dump(m), encoding="utf-8")
    with pytest.raises(ManifestError, match="no connected Unclassified branch"):
        load_manifest(str(p))


def test_system_name_collision_raises(tmp_path):
    m = yaml.safe_load(_manifest(tmp_path).read_text(encoding="utf-8"))
    m["canvases"][0]["nodes"][0]["config"]["branch_intents"] = {"Positive": ["PaidCash"]}
    m["canvases"][0]["edges"] = [
        {"from": "ask", "branch": "Positive", "to": "thanks"},
        {"from": "ask", "branch": "Unclassified", "to": "retry"},
        {"from": "thanks", "branch": "Unclassified", "to": "bye"},
        {"from": "retry", "branch": "Unclassified", "to": "bye"},
    ]
    p = tmp_path / "m3.yaml"
    p.write_text(yaml.safe_dump(m), encoding="utf-8")
    with pytest.raises(ManifestError, match="collides"):
        load_manifest(str(p))
