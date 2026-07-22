"""Content-hash LRU memoization for pure functions of a single dict/list arg.

Turns run in worker threads and this cache is module-global across tenants, so
access is lock-guarded. Results are deep-copied on return so a caller mutating a
result never corrupts a later cache hit."""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from collections import OrderedDict


def content_key(data) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def bounded_memo(maxsize: int = 16):
    def deco(fn):
        cache: "OrderedDict[str, object]" = OrderedDict()
        lock = threading.Lock()

        def wrapper(data):
            key = content_key(data)
            with lock:
                if key in cache:
                    cache.move_to_end(key)
                    return copy.deepcopy(cache[key])
            result = fn(data)
            with lock:
                cache[key] = result
                cache.move_to_end(key)
                while len(cache) > maxsize:
                    cache.popitem(last=False)
                return copy.deepcopy(result)

        wrapper.__wrapped__ = fn
        wrapper.cache_clear = cache.clear
        return wrapper

    return deco
