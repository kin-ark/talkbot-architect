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


_LEVEL_COLOR = {
    "DEBUG": "\033[38;5;244m", "INFO": "\033[36m", "WARNING": "\033[33m",
    "ERROR": "\033[31m", "CRITICAL": "\033[97;41m",
}
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


class PrettyFormatter(logging.Formatter):
    """Human-readable one-line console format: `HH:MM:SS LVL  ev msg  k=v …`.

    Colors (level tint, dim timestamp/keys) only when `color=True`; layout is
    identical without color, so it stays readable when piped to a file.
    """

    def __init__(self, color: bool = True) -> None:
        super().__init__()
        self.color = color

    def _c(self, s: str, code: str) -> str:
        return f"{code}{s}{_RESET}" if self.color else s

    def format(self, record: logging.LogRecord) -> str:
        try:
            ts = time.strftime("%H:%M:%S", time.localtime(record.created))
            lvl = record.levelname
            head = f"{self._c(ts, _DIM)} {self._c(f'{lvl:<5}', _LEVEL_COLOR.get(lvl, ''))}"
            ev = getattr(record, "ev", None)
            evtag = self._c(str(ev), _BOLD) if ev else ""
            msg = record.getMessage()
            parts = []
            for k in _EXTRA_KEYS:
                if k == "ev" or not hasattr(record, k):
                    continue
                parts.append(f"{self._c(k + '=', _DIM)}{getattr(record, k)}")
            body = " ".join(x for x in (evtag, msg) if x)
            line = f"{head}  {body}" if body else head
            if parts:
                line += "  " + " ".join(parts)
            if record.exc_info:
                line += "\n" + self.formatException(record.exc_info)
            return line
        except Exception:
            try:
                return record.getMessage()
            except Exception:
                return ""


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

    # Console: pretty by default when attached to a terminal (dev); JSON when
    # piped/redirected or in Docker. LOG_PRETTY=1/0 forces it on/off.
    is_tty = bool(getattr(sys.stdout, "isatty", lambda: False)())
    env_pretty = os.environ.get("LOG_PRETTY")
    if env_pretty == "1":
        use_pretty = True
    elif env_pretty == "0":
        use_pretty = False
    else:
        use_pretty = is_tty

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(PrettyFormatter(color=is_tty) if use_pretty else fmt)
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
