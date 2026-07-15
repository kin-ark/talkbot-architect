import agents


def test_returns_bounded_ranked_slice():
    r = agents.get_debt_corpus("intents", top_n=5)
    assert r["found"] is True
    assert r["section"] == "intents"
    assert 0 < len(r["items"]) <= 5
    # ranked: counts non-increasing
    counts = [it["count"] for it in r["items"]]
    assert counts == sorted(counts, reverse=True)


def test_top_n_clamped_to_30():
    r = agents.get_debt_corpus("kbs", top_n=1000)
    assert len(r["items"]) <= 30


def test_top_n_floor_and_default():
    assert len(agents.get_debt_corpus("intents", top_n=0)["items"]) >= 1  # clamped up to 1
    assert agents.get_debt_corpus("intents")["found"] is True             # default top_n works


def test_unknown_section_errors_with_options():
    r = agents.get_debt_corpus("bogus")
    assert "error" in r
    assert "intents" in r["sections"] and "tag_patterns" in r["sections"]


def test_stage_filter_on_stage_deltas():
    r = agents.get_debt_corpus("stage_deltas", stage="dpd1_5")
    assert r["found"] is True
    assert all(d.get("stage") == "dpd1_5" for d in r["items"])


def test_missing_corpus_returns_not_found(monkeypatch, tmp_path):
    # point the reader at a non-existent file
    monkeypatch.setattr(agents, "_DEBT_CORPUS_PATH", tmp_path / "nope.json")
    assert agents.get_debt_corpus("intents") == {"found": False}


def test_corrupt_corpus_returns_not_found(monkeypatch, tmp_path):
    bad = tmp_path / "corrupt.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    monkeypatch.setattr(agents, "_DEBT_CORPUS_PATH", bad)
    assert agents.get_debt_corpus("intents") == {"found": False}


def test_non_int_top_n_falls_back_to_default():
    assert agents.get_debt_corpus("intents", top_n=None)["found"] is True
    assert agents.get_debt_corpus("intents", top_n="x")["found"] is True
    # both fall back to default 15 (bounded)
    assert len(agents.get_debt_corpus("intents", top_n=None)["items"]) <= 15
