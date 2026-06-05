import pytest
from wizmodifier.registry import OP_REGISTRY, get_op


def test_all_phase1_ops_registered():
    expected = {
        "set-speech-id", "set-component-uuid", "set-bsc-name", "set-bsc-id",
        "add-bsc-keys", "populate-details", "add-component",
        "add-variable", "add-intent", "set-path", "delete-path",
    }
    assert expected <= set(OP_REGISTRY)


def test_get_op_unknown_raises():
    with pytest.raises(ValueError, match="no-such-op"):
        get_op("no-such-op")
