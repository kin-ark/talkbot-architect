import json
import logging
import logging_setup
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_jsonformatter_emits_valid_json_with_extras():
    fmt = logging_setup.JsonFormatter()
    rec = logging.LogRecord("tba", logging.INFO, __file__, 1, "", (), None)
    rec.ev = "req"
    rec.method = "GET"
    rec.path = "/x"
    rec.status = 200
    rec.ms = 3
    obj = json.loads(fmt.format(rec))
    assert obj["ev"] == "req" and obj["method"] == "GET" and obj["status"] == 200
    assert "ts" in obj and obj["lvl"] == "INFO"


def test_jsonformatter_renders_exc_info_trace():
    fmt = logging_setup.JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        rec = logging.LogRecord("tba", logging.ERROR, __file__, 1, "", (), sys.exc_info())
        rec.ev = "exc"
    obj = json.loads(fmt.format(rec))
    assert obj["ev"] == "exc" and "boom" in obj["trace"]


def test_jsonformatter_never_raises_on_bad_extra():
    fmt = logging_setup.JsonFormatter()
    rec = logging.LogRecord("tba", logging.INFO, __file__, 1, "hi", (), None)
    rec.ev = "req"
    rec.err = object()          # non-serializable
    out = fmt.format(rec)                         # must not raise
    assert isinstance(out, str) and len(out) > 0


def test_configure_logging_idempotent():
    logging_setup._configured = False
    logging_setup.configure_logging()
    n = len(logging.getLogger("tba").handlers)
    logging_setup.configure_logging()
    assert len(logging.getLogger("tba").handlers) == n   # no duplicate handlers


def test_configure_logging_survives_unwritable_log_dir(monkeypatch):
    monkeypatch.setenv("LOG_DIR", "/proc/nonexistent/cannot-make")   # makedirs will fail
    logging_setup._configured = False
    logging_setup.configure_logging()                                # must not raise
    handlers = logging.getLogger("tba").handlers
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)   # stdout still attached


def test_request_log_middleware_logs_requests_but_not_health():
    app = FastAPI()
    app.add_middleware(logging_setup.RequestLogMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    logging_setup._configured = False
    logging_setup.configure_logging()

    # Attach a custom handler to capture records on the 'tba' logger.
    records = []
    class ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = ListHandler()
    handler.setLevel(logging.INFO)
    logging_setup.log.addHandler(handler)

    try:
        client = TestClient(app)
        client.get("/ping")
        client.get("/health")

        reqs = [r for r in records if getattr(r, "ev", None) == "req"]
        assert len(reqs) == 1                          # /ping logged, /health not
        assert reqs[0].path == "/ping" and reqs[0].status == 200
    finally:
        logging_setup.log.removeHandler(handler)


def test_health_returns_richer_body():
    import main
    with TestClient(main.app) as client:
        body = client.get("/health").json()
    assert body["status"] == "ok"
    assert isinstance(body["live_sessions"], int)
    assert isinstance(body["uptime_s"], int)


def test_unhandled_exception_is_logged():
    import main
    # Register a throwaway route that raises, then hit it and assert an exc log.
    @main.app.get("/_boom_test")
    def _boom():
        raise RuntimeError("kaboom")

    logging_setup._configured = False
    logging_setup.configure_logging()

    # Attach a custom handler to capture records on the 'tba' logger.
    records = []
    class ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = ListHandler()
    handler.setLevel(logging.ERROR)
    logging_setup.log.addHandler(handler)

    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            r = client.get("/_boom_test")
        assert r.status_code == 500
        excs = [rec for rec in records if getattr(rec, "ev", None) == "exc"]
        assert excs and "kaboom" in (excs[-1].err or "")
    finally:
        logging_setup.log.removeHandler(handler)
