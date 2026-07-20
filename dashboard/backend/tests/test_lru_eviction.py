"""Per-cookie config + session stores are LRU-capped (no unbounded growth)."""
import config_store
import persistence
from registry import Registry


def test_config_store_evicts_least_recently_used(monkeypatch):
    monkeypatch.setattr(config_store, "_MAX_CONFIGS", 2)
    monkeypatch.setattr(config_store, "_CONFIGS", type(config_store._CONFIGS)())
    a = config_store.config_for("a")
    config_store.config_for("b")
    config_store.config_for("a")          # touch 'a' -> now 'b' is oldest
    config_store.config_for("c")          # over cap -> evict 'b'
    keys = list(config_store._CONFIGS.keys())
    assert set(keys) == {"a", "c"}
    assert config_store.config_for("a") is a   # 'a' survived (same object)


def test_registry_evicts_least_recently_used(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path)
    import registry as reg
    monkeypatch.setattr(reg, "_MAX_STORES", 2)
    r = Registry()
    r.store("a")
    r.store("b")
    r.store("a")          # touch 'a'
    r.store("c")          # evict 'b'
    assert set(r._stores.keys()) == {"a", "c"}
