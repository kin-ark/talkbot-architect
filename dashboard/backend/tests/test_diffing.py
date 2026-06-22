from diffing import unified_diff_of, checker_delta


def test_unified_diff_shows_changed_value():
    before = {"a": "1", "b": "x"}
    after = {"a": "2", "b": "x"}
    d = unified_diff_of(before, after)
    assert "-" in d and "+" in d and "2" in d


def test_no_change_empty_diff():
    assert unified_diff_of({"a": "1"}, {"a": "1"}) == ""
