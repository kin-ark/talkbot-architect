import json
import pathlib
import agents

# a real tagged export (4 SpeechTag categories)
_ZIP = pathlib.Path(__file__).resolve().parents[3] / "talkbot" / "Debt Collection" / "[RELEASED]+TokoKapital+DPD0.zip"


def _tagged_data():
    import zipfile
    z = zipfile.ZipFile(_ZIP)
    n = next(x for x in z.namelist() if x.startswith("speech") and x.endswith(".json"))
    return json.loads(z.read(n))


def test_list_tags_reports_categories():
    if not _ZIP.exists():
        import pytest; pytest.skip("tagged corpus fixture absent")
    tags = agents.list_tags(_tagged_data())
    assert isinstance(tags, list) and tags
    row = tags[0]
    assert set(row) >= {"category", "category_id", "values", "node_count"}
    assert row["category"] and isinstance(row["values"], list)


def test_list_tags_empty_bot():
    assert agents.list_tags({"BizSpeechComponent": []}) == []


def test_list_tags_never_raises_on_junk():
    assert agents.list_tags({"SpeechTag": "not-json"}) == []


def test_summarize_attaches_tags():
    if not _ZIP.exists():
        import pytest; pytest.skip("tagged corpus fixture absent")
    s = agents.summarize(_tagged_data())
    assert "tags" in s and isinstance(s["tags"], list)
    # every node has a (possibly empty) tags list of {category,value}
    for comp in s.get("components", []):
        for node in (comp.get("nodes") or {}).values():
            assert "tags" in node and isinstance(node["tags"], list)
    # at least one node carries a tag (this bot tags dispositions)
    any_tag = any(node.get("tags")
                  for comp in s["components"] for node in (comp.get("nodes") or {}).values())
    assert any_tag
