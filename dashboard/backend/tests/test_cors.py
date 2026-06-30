"""CORS regression: with credentials, the dev origin must get an
Access-Control-Allow-Origin header (else the browser blocks every call)."""
from fastapi.testclient import TestClient
import main


def test_dev_origin_gets_cors_headers():
    with TestClient(main.app) as client:
        r = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 200
        # The credentialed cross-origin request must be allowed for the dev origin.
        assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert r.headers.get("access-control-allow-credentials") == "true"


def test_preflight_allowed_for_dev_origin():
    with TestClient(main.app) as client:
        r = client.options(
            "/session/blank",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert r.status_code in (200, 204)
        assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
