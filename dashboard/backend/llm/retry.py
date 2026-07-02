"""Provider-agnostic retry/backoff for transient LLM API errors."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


def retry_after_seconds(exc: Exception) -> float | None:
    """Read a Retry-After header (seconds) off an SDK exception. Never raises."""
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None)
    if not headers:
        return None
    try:
        val = headers.get("retry-after") or headers.get("Retry-After")
    except Exception:
        return None
    if val is None:
        return None
    try:
        return float(int(str(val).strip()))
    except (ValueError, TypeError):
        return None


def backoff_wait(attempt: int, base: float, retry_after_val: float | None) -> float:
    """Seconds to sleep before retry `attempt` (1-based). Retry-After wins."""
    if retry_after_val is not None and retry_after_val > 0:
        return retry_after_val
    span = base * (2 ** (attempt - 1))
    return span + span * 0.1   # flat 10% jitter, deterministic (no random)


def with_retry(
    fn: Callable[[], Any],
    *,
    attempts: int = 3,
    base: float = 1.0,
    is_retryable: Callable[[Exception], bool],
    sleep: Callable[[float], None] = time.sleep,
    retry_after: Callable[[Exception], float | None] | None = None,
) -> Any:
    """Call fn(); retry on is_retryable(exc) with exponential backoff."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — classifier decides
            attempt += 1
            if not is_retryable(e) or attempt >= attempts:
                raise
            ra = retry_after(e) if retry_after else None
            sleep(backoff_wait(attempt, base, ra))
