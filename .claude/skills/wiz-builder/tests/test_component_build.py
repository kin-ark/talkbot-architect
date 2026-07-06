import json
import tempfile
from pathlib import Path

import pytest

from wizbuilder.compile import compile_manifest, CompileError
from wizbuilder.manifest import ManifestError

_COMPONENT_MANIFEST = """
name: "Greeting Component"
branch: dev
language: IDN
canvases:
  - name: "Main"
    nodes:
      - {id: greet, type: talk, prompt: "Halo, ada yang bisa dibantu?"}
      - {id: bye, type: exit, prompt: "Terima kasih."}
    edges:
      - {from: greet, branch: Positive, to: bye}
      - {from: greet, branch: Negative, to: bye}
      - {from: greet, branch: Unclassified, to: bye}
"""

_BAD_KB_MANIFEST = _COMPONENT_MANIFEST.rstrip() + """
knowledge_bases:
  - {name: "K1", intents: [SomeIntent], answers: ["hi"]}
custom_intents:
  - {name: SomeIntent, language: IDN, keywords: ["x"], user_responses: ["x"]}
"""


def _build(manifest_text, emit):
    with tempfile.TemporaryDirectory() as d:
        mp = Path(d) / "m.yaml"; mp.write_text(manifest_text, encoding="utf-8")
        op = Path(d) / "out.json"
        compile_manifest(mp, op, emit=emit)
        return json.loads(op.read_text(encoding="utf-8"))


def test_emit_component_produces_dto_envelope():
    out = _build(_COMPONENT_MANIFEST, "component")
    assert "componentImportAndExportDTOS" in out
    assert "BizSpeechComponent" not in out
    entry = out["componentImportAndExportDTOS"][0]
    assert entry["componentName"] == "Main"
    assert isinstance(entry["speechComponentDTO"]["details"], dict)  # decoded


def test_emit_full_unchanged():
    out = _build(_COMPONENT_MANIFEST, "full")
    assert "BizSpeechComponent" in out
    assert "componentImportAndExportDTOS" not in out


def test_component_mode_rejects_knowledge_bases():
    with pytest.raises((ManifestError, CompileError), match="component mode"):
        _build(_BAD_KB_MANIFEST, "component")
