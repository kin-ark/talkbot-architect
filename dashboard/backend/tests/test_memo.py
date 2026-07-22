from memo import bounded_memo, content_key


def test_memo_computes_once_per_content():
    calls = {"n": 0}
    @bounded_memo()
    def f(d):
        calls["n"] += 1
        return {"echo": d}
    f({"a": 1}); f({"a": 1})           # equal content -> 1 compute
    assert calls["n"] == 1
    f({"a": 2})                         # different content -> recompute
    assert calls["n"] == 2


def test_memo_returns_isolated_copies():
    @bounded_memo()
    def f(d):
        return {"x": [1]}
    a = f({"k": "iso"})
    a["x"].append(99)                   # mutate the returned result
    b = f({"k": "iso"})                 # cache hit
    assert b["x"] == [1]                # not corrupted


def test_memo_evicts_beyond_maxsize():
    calls = {"n": 0}
    @bounded_memo(maxsize=2)
    def f(d):
        calls["n"] += 1
        return d
    f({"a": 1}); f({"a": 2}); f({"a": 3})   # evicts {"a":1}
    f({"a": 1})                              # recomputes (was evicted)
    assert calls["n"] == 4


def test_content_key_stable_and_order_insensitive():
    assert content_key({"a": 1, "b": 2}) == content_key({"b": 2, "a": 1})
    assert content_key({"a": 1}) != content_key({"a": 2})


def test_validate_memoized(monkeypatch):
    import agents
    agents.validate.cache_clear()
    calls = {"n": 0}
    real = agents.parse_dict
    def counting(d):
        calls["n"] += 1
        return real(d)
    monkeypatch.setattr(agents, "parse_dict", counting)
    doc = {"BizSpeechComponent": "[]", "_memo_probe": "unique-1"}
    r1 = agents.validate(doc)
    r2 = agents.validate(dict(doc))     # equal content -> cache hit
    assert calls["n"] == 1
    assert r1 == r2
