import json
from pathlib import Path

from wizmodifier.io import InputBundle, write_output

FIXT = Path(__file__).parent / "fixtures" / "component_export.json"


def test_load_detects_component_and_adapts():
    bundle = InputBundle.load(FIXT)
    assert bundle.is_component is True
    assert bundle.component_source is not None
    # adapted to full-export shape ops understand
    assert "BizSpeechComponent" in bundle.data


def test_load_full_export_is_not_component():
    full = Path(__file__).parent / "fixtures" / "speech4010869963530658988.json"
    bundle = InputBundle.load(full)
    assert bundle.is_component is False
    assert bundle.component_source is None


def test_write_noop_roundtrip_preserves_envelope(tmp_path):
    original = json.loads(FIXT.read_text(encoding="utf-8"))
    bundle = InputBundle.load(FIXT)
    out = tmp_path / "out.json"
    write_output(bundle, out, fmt="json")
    result = json.loads(out.read_text(encoding="utf-8"))
    # top-level envelope shape preserved
    assert set(result) == set(original)
    assert result["name"] == original["name"]
    assert result["speechEntiEntityList"] == original["speechEntiEntityList"]
    assert (len(result["componentImportAndExportDTOS"])
            == len(original["componentImportAndExportDTOS"]))


def test_write_component_rejects_zip(tmp_path):
    import pytest
    bundle = InputBundle.load(FIXT)
    with pytest.raises(ValueError, match="JSON only"):
        write_output(bundle, tmp_path / "out.zip", fmt="zip")
