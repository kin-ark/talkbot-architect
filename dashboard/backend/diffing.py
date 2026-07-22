"""Human-readable diffs + checker deltas between two export dicts."""
from __future__ import annotations

import difflib
import json

import agents
from memo import bounded_memo


@bounded_memo()
def normalize_for_diff(data: dict) -> str:
    """Pretty-print, expanding nested JSON-encoded string values for readability."""
    def expand(v):
        if isinstance(v, str):
            s = v.strip()
            if s and s[0] in "[{":
                try:
                    return expand(json.loads(s))
                except json.JSONDecodeError:
                    return v
            return v
        if isinstance(v, dict):
            return {k: expand(x) for k, x in v.items()}
        if isinstance(v, list):
            return [expand(x) for x in v]
        return v
    return json.dumps(expand(data), indent=2, ensure_ascii=False, sort_keys=True)


def unified_diff_of(before: dict, after: dict) -> str:
    b = normalize_for_diff(before).splitlines(keepends=True)
    a = normalize_for_diff(after).splitlines(keepends=True)
    if b == a:
        return ""
    return "".join(difflib.unified_diff(b, a, fromfile="current", tofile="proposed", n=3))


def checker_delta(before: dict, after: dict) -> dict:
    fb, fa = agents.validate(before), agents.validate(after)
    def counts(fs):
        return (sum(f["severity"] == "error" for f in fs),
                sum(f["severity"] == "warning" for f in fs))
    eb, wb = counts(fb)
    ea, wa = counts(fa)
    return {"errors_before": eb, "errors_after": ea,
            "warnings_before": wb, "warnings_after": wa,
            "new_error_codes": sorted({f["code"] for f in fa if f["severity"] == "error"}
                                      - {f["code"] for f in fb if f["severity"] == "error"})}
