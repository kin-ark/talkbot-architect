import os
import importlib
from fastapi.testclient import TestClient


def _client(monkeypatch, password):
    if password is None:
        monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("DASHBOARD_PASSWORD", password)
    import main, auth  # noqa
    importlib.reload(auth)
    importlib.reload(main)
    return TestClient(main.app)


def test_health_exempt_from_auth(monkeypatch):
    c = _client(monkeypatch, "secret")
    assert c.get("/health").status_code == 200


def test_protected_route_401_without_auth(monkeypatch):
    c = _client(monkeypatch, "secret")
    r = c.get("/config")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_protected_route_200_with_correct_basic(monkeypatch):
    c = _client(monkeypatch, "secret")
    r = c.get("/config", auth=("admin", "secret"))
    assert r.status_code == 200


def test_wrong_password_401(monkeypatch):
    c = _client(monkeypatch, "secret")
    assert c.get("/config", auth=("admin", "nope")).status_code == 401


def test_no_password_env_means_open(monkeypatch):
    c = _client(monkeypatch, None)
    assert c.get("/config").status_code == 200


def test_spa_mount_absent_in_dev_is_noop(monkeypatch):
    """App constructs cleanly without a static/ dir (dev mode)."""
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    import main, auth  # noqa
    importlib.reload(auth)
    importlib.reload(main)
    # The 'spa' mount is registered IFF static/ exists. Assert the guard holds
    # in BOTH directions (no tautology) — and that /health still works regardless.
    static_dir = os.path.join(os.path.dirname(main.__file__), "static")
    route_names = [r.name for r in main.app.routes if hasattr(r, "name")]
    assert ("spa" in route_names) == os.path.isdir(static_dir)
    assert TestClient(main.app).get("/health").status_code == 200
