from wizmodifier import codec
from wizmodifier.apply import run_mods
from wizmodifier.io import InputBundle


def test_zero_ops_is_byte_identical_after_reserialize(baseline_json_path):
    """A no-op run must equal the re-serialized baseline exactly (no noise)."""
    b = InputBundle.load(baseline_json_path)
    reserialized = codec.encode(codec.decode(codec.encode(b.data)))  # canonical form
    run_mods(b, [], manifest_hash="t")
    assert b.serialize_json() == reserialized


def test_untouched_fields_unchanged(baseline_json_path):
    b = InputBundle.load(baseline_json_path)
    before = dict(b.data)
    run_mods(b, [{"op": "set-bsc-name", "component": 0, "value": "X"}], manifest_hash="t")
    # Only BizSpeechComponent should differ.
    changed = [k for k in before if before[k] != b.data[k]]
    assert changed == ["BizSpeechComponent"]


def test_ops_apply_in_order(baseline_json_path):
    b = InputBundle.load(baseline_json_path)
    run_mods(
        b,
        [
            {"op": "set-bsc-name", "component": 0, "value": "First"},
            {"op": "set-bsc-name", "component": 0, "value": "Second"},
        ],
        manifest_hash="t",
    )
    assert codec.decode(b.data["BizSpeechComponent"])[0]["name"] == "Second"


def test_unknown_op_in_mods_raises(baseline_json_path):
    import pytest

    b = InputBundle.load(baseline_json_path)
    with pytest.raises(ValueError, match="frobnicate"):
        run_mods(b, [{"op": "frobnicate"}], manifest_hash="t")


def test_missing_target_error_is_prefixed(baseline_json_path):
    import pytest

    b = InputBundle.load(baseline_json_path)
    with pytest.raises(ValueError, match="mod #1"):
        run_mods(b, [{"op": "set-bsc-name", "component": 5, "value": "X"}], manifest_hash="t")
