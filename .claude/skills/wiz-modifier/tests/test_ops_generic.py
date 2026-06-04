import pytest
from wizmodifier import codec
from wizmodifier.io import InputBundle
from wizmodifier.ops import generic


def _bundle():
    data = {"SpeechRules": codec.encode({"a": {"b": [10, 20]}})}
    return InputBundle(data=data, speech_name="s.json")


def test_set_path_existing():
    b = _bundle()
    generic.set_path(b, {"key": "SpeechRules", "pointer": ["a", "b", 1], "value": 99}, None)
    assert codec.decode(b.data["SpeechRules"])["a"]["b"][1] == 99


def test_set_path_create_new_key():
    b = _bundle()
    generic.set_path(
        b,
        {"key": "SpeechRules", "pointer": ["a", "c"], "value": 5, "create": True},
        None,
    )
    assert codec.decode(b.data["SpeechRules"])["a"]["c"] == 5


def test_set_path_missing_without_create_raises():
    b = _bundle()
    with pytest.raises(ValueError, match="create"):
        generic.set_path(b, {"key": "SpeechRules", "pointer": ["a", "z"], "value": 1}, None)


def test_delete_path():
    b = _bundle()
    generic.delete_path(b, {"key": "SpeechRules", "pointer": ["a", "b"]}, None)
    assert codec.decode(b.data["SpeechRules"])["a"] == {}
