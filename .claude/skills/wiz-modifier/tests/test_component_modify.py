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


def _errors(envelope_dict):
    """Extract ERROR-severity findings from a component-export dict."""
    from wizcheck.checks import run_all_checks
    from wizcheck.parser import parse_dict
    wf = parse_dict(envelope_dict)
    findings = run_all_checks(wf)
    return [f for f in findings if getattr(f, "severity", "") == "error"]


def test_modify_component_rename_node_roundtrips_clean(tmp_path):
    """Load component -> apply rename-node op -> write -> re-parse -> 0 errors."""
    from wizmodifier.apply import run_mods
    bundle = InputBundle.load(FIXT)
    # rename the entry talk node's label; the fixture node label is "Talk Node"
    # component=0 is the only component in the fixture
    # node ref uses {"label": "Talk Node"} format
    mods = [{"op": "rename-node", "component": 0,
             "node": {"label": "Talk Node"}, "label": "Welcome"}]
    run_mods(bundle, mods, manifest_hash="h")
    out = tmp_path / "out.json"
    write_output(bundle, out, fmt="json")
    result = json.loads(out.read_text(encoding="utf-8"))
    # envelope shape preserved
    assert "componentImportAndExportDTOS" in result
    # new label appears in the output
    assert "Welcome" in json.dumps(result)
    # round-trip validates clean (0 error-severity findings)
    assert _errors(result) == []


def test_modify_component_add_variable_roundtrips_clean(tmp_path):
    """Load component -> add-variable -> write -> re-parse -> 0 errors + variable present."""
    from wizmodifier.apply import run_mods
    bundle = InputBundle.load(FIXT)
    mods = [{"op": "add-variable", "name": "Score", "textType": "DEFAULT"}]
    run_mods(bundle, mods, manifest_hash="h")
    out = tmp_path / "out.json"
    write_output(bundle, out, fmt="json")
    result = json.loads(out.read_text(encoding="utf-8"))
    # new variable present in envelope
    names = [v.get("name") for v in result.get("speechVariableDTO", [])]
    assert "Score" in names
    # round-trip validates clean
    assert _errors(result) == []


def test_guard_rejects_add_component_forbidden_node():
    """Guard rejects add-component with forbidden node type (goto_kb, goto_mr, talk_continue)."""
    import pytest
    from wizmodifier.apply import run_mods
    bundle = InputBundle.load(FIXT)
    # add-component with a goto_kb node (forbidden in component mode)
    mods = [{"op": "add-component", "name": "NewComponent",
             "nodes": [{"id": "n1", "type": "goto_kb", "config": {"target": "SomeKB"}}]}]
    with pytest.raises(ValueError, match="component mode"):
        run_mods(bundle, mods, manifest_hash="_")


def test_modify_component_rewire_edge_roundtrips_clean(tmp_path):
    """Load component -> apply rewire-edge op -> write -> re-parse -> 0 errors."""
    from wizmodifier.apply import run_mods
    bundle = InputBundle.load(FIXT)
    # Fixture has a talk node (uuid c8a8f42b-1524-54b6-acb9-cb57d35ccfc7) with branches
    # Positive, Negative, Unclassified. Only Unclassified is routed to the exit.
    # Rewire the Negative branch to the exit node.
    mods = [{"op": "rewire-edge", "component": 0,
             "from": {"label": "Talk Node"},
             "branch": "Negative",
             "to": {"label": "Exit Node"}}]
    run_mods(bundle, mods, manifest_hash="h")
    out = tmp_path / "out.json"
    write_output(bundle, out, fmt="json")
    result = json.loads(out.read_text(encoding="utf-8"))
    # envelope shape preserved
    assert "componentImportAndExportDTOS" in result
    # round-trip validates clean (0 error-severity findings)
    assert _errors(result) == []


def test_modify_component_key_set_preserved_no_spurious_keys(tmp_path):
    """Modify a component without topFloorDetails, apply rename-node, verify key set unchanged."""
    # Build a minimal component-export without topFloorDetails (simulates a source
    # that the modifier receives).
    comp_export_no_topfloor = {
        "name": "Minimal",
        "componentImportAndExportDTOS": [{
            "componentName": "Greeting",
            "componentUuid": "11111111-1111-1111-1111-111111111111",
            "speechId": 12345,
            "templateCode": "T_test",
            "enterpriseId": 0,
            "asrSceneEntityList": [],
            "speechComponentDTO": {
                "componentUuid": "11111111-1111-1111-1111-111111111111",
                "name": "Greeting",
                "branch": "dev",
                "category": 1,
                "type": 1,
                "editStatus": 1,
                "useStatus": 1,
                "parentUuid": "0",
                "sortIndex": 1,
                "speechId": 12345,
                "templateCode": "T_test",
                "updateTime": 1000,
                "updateBy": 999,
                "id": 888,
                "version": "4",
                "inboundPorts": [{"name": "Entry", "type": 1, "uuid": "22222222-2222-2222-2222-222222222222", "is_default": True}],
                "outboundPorts": [],
                "routes": {"22222222-2222-2222-2222-222222222222": {}},
                "nluConf": {},
                "sourceUuid": "",
                "details": {"22222222-2222-2222-2222-222222222222": {
                    "type": 1,
                    "data": {
                        "type": 1,
                        "name": "Entry",
                        "list": ["Hello"]
                    }
                }},
                # NOTE: no topFloorDetails key
            },
            "sentenceCutDTOList": [{
                "id": "22222222-2222-2222-2222-222222222222",
                "componentUuid": "11111111-1111-1111-1111-111111111111",
                "sentence_text": "Hello",
                "sen_rec_name": "",
                "sentence_text_url": "",
                "speech_rec_cut_id": "rec-001",
                "is_delete": 0,
                "sentenceCutId": 777,
                "showType": 0,
                "sortIndex": 1,
                "type": "record",
            }],
        }],
        "speechIntentDTO": [
            {"intentId": 1, "intentName": "Unclassified", "isInit": 0, "language": "IDN",
             "keyWordInIntent": [], "userResponseInIntent": []},
        ],
        "speechVariableDTO": [],
        "speechEntiEntityList": [],
        "speechEntityData": [],
        "speechFunctionDTO": [],
        "tagDTOList": [],
    }

    # Write to temp file and load
    in_file = tmp_path / "in.json"
    in_file.write_text(json.dumps(comp_export_no_topfloor), encoding="utf-8")

    # Load and apply rename-node op
    from wizmodifier.apply import run_mods
    bundle = InputBundle.load(in_file)
    assert bundle.is_component is True

    # Record the input key set
    input_scd = comp_export_no_topfloor["componentImportAndExportDTOS"][0]["speechComponentDTO"]
    input_keys = set(input_scd.keys())

    # Apply a rename-node op (rename node "Entry" to "Welcome")
    mods = [{"op": "rename-node", "component": 0,
             "node": {"label": "Entry"},
             "label": "Welcome"}]
    run_mods(bundle, mods, manifest_hash="test-hash")

    # Write output
    out_file = tmp_path / "out.json"
    write_output(bundle, out_file, fmt="json")

    # Re-parse output and verify key set unchanged + rename worked
    result = json.loads(out_file.read_text(encoding="utf-8"))
    output_scd = result["componentImportAndExportDTOS"][0]["speechComponentDTO"]
    output_keys = set(output_scd.keys())

    # Key set should be identical (no spurious topFloorDetails or other keys added)
    assert output_keys == input_keys, f"Key set changed: input={input_keys}, output={output_keys}"
    assert "topFloorDetails" not in output_keys, "topFloorDetails should NOT be present"

    # Verify round-trip validates clean
    assert _errors(result) == []
