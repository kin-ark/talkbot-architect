"""SSRF guard on the custom base_url (PUT /config)."""
from fastapi.testclient import TestClient
import main


def _client():
    c = TestClient(main.app)
    c.get("/health")   # mint tbid cookie
    return c


def test_rejects_cloud_metadata_ip():
    with _client() as c:
        r = c.put("/config", json={"model_id": "claude-opus-4-8",
                                   "base_url": "http://169.254.169.254/latest"})
    assert r.status_code == 400


def test_rejects_non_http_scheme():
    with _client() as c:
        r = c.put("/config", json={"model_id": "claude-opus-4-8",
                                   "base_url": "ftp://example.com/x"})
    assert r.status_code == 400


def test_allows_private_gateway():
    """A private/VPN gateway IP must still be accepted (the real deployment
    points at a private address)."""
    with _client() as c:
        r = c.put("/config", json={"model_id": "claude-opus-4-8",
                                   "base_url": "http://10.0.3.248:3000/api"})
    assert r.status_code == 200


def test_empty_base_url_ok():
    with _client() as c:
        r = c.put("/config", json={"model_id": "claude-opus-4-8", "base_url": ""})
    assert r.status_code == 200
