import json
from pathlib import Path

from analysis import debt_mine

_FIX = Path(__file__).resolve().parents[1] / "samples" / "debt_collection_dpd1_5.yaml"  # any manifest -> build to a real export


def _one_export():
    # Build a real export dict from a known-good sample manifest (no corpus ZIP needed).
    import agents
    built = agents.propose_build(_FIX.read_text(encoding="utf-8"))
    assert built["ok"], built.get("error")
    return built["proposed_data"]


def test_scrub_redacts_pii():
    s = debt_mine.scrub("Bayar Rp1.250.000 sebelum 12/05/2026, VA 8801234567, a@b.com")
    assert "1.250.000" not in s and "8801234567" not in s
    assert "12/05/2026" not in s and "a@b.com" not in s
    assert "{" in s  # placeholders inserted


def test_stage_from_name():
    assert debt_mine.stage_from_name("[Main]+Overdue+DPD1-5.zip") == "dpd1_5"
    assert debt_mine.stage_from_name("Payment+Reminder+Predue+D-1.zip") == "predue_d1"
    assert debt_mine.stage_from_name("PTP+Reminder.zip") == "ptp_reminder"
    assert debt_mine.stage_from_name("Some+Generic+Bot.zip") == "mixed"


def test_mine_and_aggregate_shape():
    rec = debt_mine.mine_bot(_one_export(), stage="dpd1_5")
    assert isinstance(rec["intents"], list) and isinstance(rec["kbs"], list)
    corpus = debt_mine.aggregate([rec])
    for key in ("meta", "intents", "kbs", "script_archetypes",
                "flow_engines", "stage_deltas", "objection_map", "tag_patterns"):
        assert key in corpus, f"missing {key}"
    assert corpus["meta"]["bots_parsed"] == 1
    # counts present + numeric
    for it in corpus["intents"]:
        assert isinstance(it["count"], int) and 0.0 <= it["pct"] <= 1.0


def test_committed_corpus_shape_and_no_pii():
    p = Path(__file__).resolve().parents[1] / "playbooks" / "debt_collection.corpus.json"
    if not p.exists():
        import pytest
        pytest.skip("corpus json not generated in this environment")
    corpus = json.loads(p.read_text(encoding="utf-8"))
    for key in ("meta", "intents", "kbs", "script_archetypes",
                "flow_engines", "stage_deltas", "objection_map", "tag_patterns"):
        assert key in corpus
    assert corpus["meta"]["bots_parsed"] >= 25   # most of the 33 parsed
    # PII gate: no long digit-run survives in any script/answer text
    import re
    blob = json.dumps(corpus, ensure_ascii=False)
    assert not re.search(r"\d{6,}", blob), "un-scrubbed long number leaked into corpus json"
