import main


def test_get_client_caches_same_config(monkeypatch):
    main._client_cache.clear()
    calls = {"n": 0}
    class _Fake: pass
    def fake_make(**kw):
        calls["n"] += 1
        return _Fake()
    monkeypatch.setattr(main, "make_client", fake_make)
    monkeypatch.setattr(main, "_resolve_model", lambda cfg: ("anthropic", "claude-x", None))
    cid = "cache-cid-1"
    cfg = main.config_store.config_for(cid)
    cfg.api_key = "k1"
    c1 = main.get_client(cid=cid)
    c2 = main.get_client(cid=cid)
    assert c1 is c2 and calls["n"] == 1


def test_get_client_rebuilds_on_config_change(monkeypatch):
    main._client_cache.clear()
    calls = {"n": 0}
    def fake_make(**kw):
        calls["n"] += 1
        return object()
    monkeypatch.setattr(main, "make_client", fake_make)
    monkeypatch.setattr(main, "_resolve_model", lambda cfg: ("anthropic", "claude-x", None))
    cid = "cache-cid-2"
    cfg = main.config_store.config_for(cid)
    cfg.api_key = "k1"
    main.get_client(cid=cid)
    cfg.api_key = "k2"                 # rotate key -> new fingerprint
    main.get_client(cid=cid)
    assert calls["n"] == 2


def test_get_client_config_error_still_503(monkeypatch):
    from fastapi import HTTPException
    from llm.factory import LLMConfigError
    main._client_cache.clear()
    def boom(cfg): raise LLMConfigError("no model configured")
    monkeypatch.setattr(main, "_resolve_model", boom)
    import pytest
    with pytest.raises(HTTPException) as ei:
        main.get_client(cid="cache-cid-3")
    assert ei.value.status_code == 503
