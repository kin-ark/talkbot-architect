from tools import registry


def _names():
    return {t.name for t in registry.tool_specs()}


def test_three_tools_registered():
    assert {"list_samples", "get_sample", "get_debt_corpus"} <= _names()


def test_list_samples_dispatch():
    out = registry.dispatch("list_samples", {}, {})
    assert out["proposal"] is None
    ids = {e["id"] for e in out["result"]}
    assert "debt_collector" in ids


def test_get_sample_known_and_unknown():
    ok = registry.dispatch("get_sample", {"sample_id": "debt_dpd1_5"}, {})
    assert ok["proposal"] is None
    assert "custom_intents" in ok["result"]["manifest_yaml"]
    bad = registry.dispatch("get_sample", {"sample_id": "nope"}, {})
    assert "error" in bad["result"] and "available" in bad["result"]


def test_get_debt_corpus_dispatch_bounded():
    out = registry.dispatch("get_debt_corpus", {"section": "intents", "top_n": 1000}, {})
    assert out["proposal"] is None
    assert out["result"]["found"] is True
    assert len(out["result"]["items"]) <= 30


def test_get_debt_corpus_schema_has_section_enum():
    spec = next(t for t in registry.tool_specs() if t.name == "get_debt_corpus")
    enum = spec.parameters["properties"]["section"]["enum"]
    assert "intents" in enum and "tag_patterns" in enum
    assert spec.parameters["required"] == ["section"]
