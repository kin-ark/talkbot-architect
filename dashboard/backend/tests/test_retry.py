import pytest
from llm import retry


class _Retryable(Exception):
    pass


def _is_retryable(e):
    return isinstance(e, _Retryable)


def test_succeeds_first_try_no_sleep():
    calls = {"n": 0}
    slept = []
    def fn():
        calls["n"] += 1
        return "ok"
    out = retry.with_retry(fn, is_retryable=_is_retryable, sleep=slept.append)
    assert out == "ok" and calls["n"] == 1 and slept == []


def test_retries_then_succeeds():
    seq = [_Retryable(), _Retryable(), "ok"]
    slept = []
    def fn():
        x = seq.pop(0)
        if isinstance(x, Exception):
            raise x
        return x
    out = retry.with_retry(fn, is_retryable=_is_retryable, sleep=slept.append)
    assert out == "ok"
    assert len(slept) == 2                      # two backoffs before the 3rd try
    assert slept[0] == pytest.approx(1.1) and slept[1] == pytest.approx(2.2)


def test_non_retryable_raises_immediately():
    slept = []
    def fn():
        raise ValueError("nope")
    with pytest.raises(ValueError):
        retry.with_retry(fn, is_retryable=_is_retryable, sleep=slept.append)
    assert slept == []


def test_exhausts_and_raises():
    slept = []
    def fn():
        raise _Retryable()
    with pytest.raises(_Retryable):
        retry.with_retry(fn, attempts=3, is_retryable=_is_retryable, sleep=slept.append)
    assert len(slept) == 2                       # attempts-1 sleeps


def test_retry_after_overrides_backoff():
    class _E(Exception):
        pass
    seq = [_E(), "ok"]
    slept = []
    def fn():
        x = seq.pop(0)
        if isinstance(x, Exception):
            raise x
        return x
    out = retry.with_retry(fn, is_retryable=lambda e: True, sleep=slept.append,
                           retry_after=lambda e: 7.0)
    assert out == "ok" and slept == [7.0]


def test_retry_after_seconds_parses_and_tolerates_garbage():
    class _Resp:
        def __init__(self, h): self.headers = h
    class _E(Exception):
        def __init__(self, h): self.response = _Resp(h)
    assert retry.retry_after_seconds(_E({"retry-after": "12"})) == 12.0
    assert retry.retry_after_seconds(_E({"retry-after": "soon"})) is None
    assert retry.retry_after_seconds(_E({})) is None
    assert retry.retry_after_seconds(Exception()) is None
