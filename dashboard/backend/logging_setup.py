"""Structured JSON logging + a request-logging middleware for the dashboard.

stdlib-only. Logs go to stdout (docker logs) and a rotating file under LOG_DIR
(a mounted volume in prod). Never raises from the logging path.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Extra fields we surface as top-level JSON keys when present on the record.
_EXTRA_KEYS = ("ev", "method", "path", "status", "cid", "ms", "provider", "model", "ok", "err")

log = logging.getLogger("tba")
_configured = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            obj = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
                "lvl": record.levelname,
                "msg": record.getMessage(),
            }
            for k in _EXTRA_KEYS:
                if hasattr(record, k):
                    obj[k] = getattr(record, k)
            if record.exc_info:
                obj["trace"] = self.formatException(record.exc_info)
            return json.dumps(obj, ensure_ascii=False, default=str)
        except Exception:
            # Logging must never raise — emit the barest possible line.
            try:
                return json.dumps({"lvl": record.levelname, "msg": record.getMessage()}, default=str)
            except Exception:
                return record.getMessage()


def _backend_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    log.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    log.propagate = False
    log.handlers.clear()

    fmt = JsonFormatter()

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    log.addHandler(stream)

    log_dir = os.environ.get("LOG_DIR") or os.path.join(_backend_dir(), "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(os.path.join(log_dir, "app.log"), maxBytes=5_000_000, backupCount=5)
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError:
        # Unwritable LOG_DIR — keep stdout logging, skip the file handler.
        pass

    _configured = True


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":          # polled by the healthcheck; don't spam
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        try:
            log.info("", extra={
                "ev": "req",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "cid": getattr(request.state, "tbid", None),
                "ms": round((time.perf_counter() - start) * 1000),
            })
        except Exception:
            pass                                    # never break a good response
        return response
