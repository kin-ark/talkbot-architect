"""Perf caches: facts/schema mtime cache + /sessions metadata cache."""
import json
import agents
import persistence


def test_facts_cache_populated_and_stable():
    agents._facts_cache.clear()
    r1 = agents.get_facts("intent")
    assert len(agents._facts_cache) == 1          # parsed once, cached
    r2 = agents.get_facts("intent")
    assert r1 == r2
    assert len(agents._facts_cache) == 1          # not growing per call


def test_schema_cache_populated():
    agents._schema_cache.clear()
    s1 = agents.get_schema()
    assert "manifest_schema" in s1 and "modifier_ops" in s1
    s2 = agents.get_schema()
    assert s1 is s2                                # same cached object reused
    assert len(agents._schema_cache) == 1


def _write_session(dirpath, sid, owner="o1", name="Bot"):
    (dirpath / f"{sid}.json").write_text(
        json.dumps({"id": sid, "owner": owner, "name": name, "updated": 1,
                    "stack": [{"BizSpeechComponent": "[]"}], "usage": {}}),
        encoding="utf-8")


def test_list_sessions_caches_and_invalidates(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path)
    persistence._list_meta_cache.clear()
    _write_session(tmp_path, "s1")
    out = persistence.list_sessions("o1")
    assert len(out) == 1 and out[0]["name"] == "Bot"
    assert "owner" not in out[0]                   # owner stays internal
    assert len(persistence._list_meta_cache) == 1  # cached

    # Delete the file -> stale cache entry pruned on next list.
    (tmp_path / "s1.json").unlink()
    assert persistence.list_sessions("o1") == []
    assert len(persistence._list_meta_cache) == 0
