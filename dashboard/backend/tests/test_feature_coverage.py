import agents
import samples


PALETTE = {"talk", "conditional", "assign", "nested", "goto", "goto_kb", "goto_mr",
           "talk_continue", "transfer", "exit", "knowledge_base", "multi_round",
           "hot_words", "disposition_tags", "trained_intents"}


def test_rich_bot_reports_used_features():
    data = agents.propose_build(samples.load_manifest("debt_dpd1_5"))["proposed_data"]
    cov = agents.feature_coverage(data)
    assert set(cov) == {"used", "missing"}
    assert set(cov["used"]) | set(cov["missing"]) == PALETTE
    # debt_dpd1_5 uses: talk, conditional, assign, goto, goto_kb, talk_continue, exit, knowledge_base, multi_round, hot_words, trained_intents
    expected_used = {"talk", "exit", "conditional", "assign", "goto", "goto_kb", "talk_continue", "knowledge_base", "trained_intents", "hot_words", "multi_round"}
    assert set(cov["used"]) == expected_used
    # it has no disposition tags, nested, goto_mr, transfer → missing
    expected_missing = {"disposition_tags", "nested", "goto_mr", "transfer"}
    assert set(cov["missing"]) == expected_missing


def test_bare_bot_reports_missing():
    data = agents.propose_build(samples.load_manifest("greeting_faq"))["proposed_data"]
    cov = agents.feature_coverage(data)
    # greeting_faq uses: talk, exit, knowledge_base only
    expected_used = {"talk", "exit", "knowledge_base"}
    assert set(cov["used"]) == expected_used
    expected_missing = {"conditional", "assign", "nested", "goto", "goto_kb", "goto_mr", "talk_continue", "transfer", "multi_round", "hot_words", "disposition_tags", "trained_intents"}
    assert set(cov["missing"]) == expected_missing


def test_never_raises_on_junk():
    cov = agents.feature_coverage({"BizSpeechComponent": "not-json"})
    assert set(cov) == {"used", "missing"}
