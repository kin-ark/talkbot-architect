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


def _mods_hash():
    return "test-hash"


def test_guard_rejects_bot_scope_op():
    import pytest
    from wizmodifier.apply import run_mods
    bundle = InputBundle.load(FIXT)
    mods = [{"op": "set-hotwords", "words": ["indosat"]}]
    with pytest.raises(ValueError, match="component mode"):
        run_mods(bundle, mods, manifest_hash=_mods_hash())


def test_guard_rejects_forbidden_node_type():
    import pytest
    from wizmodifier.apply import run_mods
    bundle = InputBundle.load(FIXT)
    mods = [{"op": "append-node", "component": "Greeting",
             "node": {"id": "k", "type": "goto_kb", "config": {"target": "SomeKB"}}}]
    with pytest.raises(ValueError, match="component mode"):
        run_mods(bundle, mods, manifest_hash=_mods_hash())


def test_guard_allows_permitted_op_no_raise():
    # An allowed op passes the guard (guard does not raise "component mode" error).
    # The op itself may fail for unrelated reasons (missing fields); we assert only
    # that the GUARD does not raise.
    from wizmodifier.apply import run_mods
    bundle = InputBundle.load(FIXT)
    mods = [{"op": "rename-node", "component": "Greeting",
             "node": "Hello, this is a test.", "name": "Hi there"}]
    try:
        run_mods(bundle, mods, manifest_hash=_mods_hash())
    except ValueError as e:
        # If an error was raised, ensure it's not from the guard (not "component mode")
        assert "component mode" not in str(e), f"Guard should not raise: {e}"
