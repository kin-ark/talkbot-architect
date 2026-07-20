"""Session memoizes summarize/validate by version; invalidates on mutation."""
from session import Session

_DOC = {"BizSpeechComponent": "[]"}


def test_summary_findings_are_cached_per_version():
    s = Session()
    s.load(_DOC)
    a = s.summary()
    b = s.summary()
    assert a is b                      # same object -> cache hit
    f1 = s.findings()
    assert s.findings() is f1


def test_cache_invalidated_on_apply():
    s = Session()
    s.load(_DOC)
    before = s.summary()
    s.apply({"BizSpeechComponent": "[]"})   # new version
    after = s.summary()
    assert after is not before          # recomputed for the new version


def test_cache_reused_on_redo():
    s = Session()
    s.load(_DOC)
    s.apply({"BizSpeechComponent": "[]"})   # v1 (clears cache)
    s1 = s.summary()                         # cache v1
    s.undo()                                 # -> v0
    s.summary()                              # recompute v0 (does not clear)
    s.redo()                                 # -> v1 again
    assert s.summary() is s1                 # v1 still cached, reused
