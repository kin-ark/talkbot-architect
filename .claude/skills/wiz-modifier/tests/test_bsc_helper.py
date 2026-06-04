import pytest

from wizmodifier import codec
from wizmodifier.io import InputBundle
from wizmodifier.ops._bsc import get_components, require_component, set_components


def _bundle():
    data = {"BizSpeechComponent": codec.encode([{"name": "A"}, {"name": "B"}])}
    return InputBundle(data=data, speech_name="s.json")


def test_get_components_decodes():
    comps = get_components(_bundle())
    assert [c["name"] for c in comps] == ["A", "B"]


def test_set_components_reencodes_compact():
    b = _bundle()
    comps = get_components(b)
    comps[0]["name"] = "Z"
    set_components(b, comps)
    assert b.data["BizSpeechComponent"] == '[{"name":"Z"},{"name":"B"}]'


def test_require_component_out_of_range():
    with pytest.raises(ValueError, match="component 2 not found"):
        require_component([{"name": "A"}], 2)
