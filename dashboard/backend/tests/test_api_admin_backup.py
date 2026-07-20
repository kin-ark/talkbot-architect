import io
import importlib
import tarfile
import persistence
import backup

_HDR = {"X-Admin-Token": "atok"}


def _reload_main(monkeypatch, admin_token=None, password=None):
    """Reload main/auth with a chosen ADMIN_TOKEN (and optional password).
    Admin endpoints are gated by ADMIN_TOKEN; the password gate is separate."""
    if password is None:
        monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("DASHBOARD_PASSWORD", password)
    if admin_token is None:
        monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    else:
        monkeypatch.setenv("ADMIN_TOKEN", admin_token)
    import main
    import auth
    importlib.reload(auth)
    importlib.reload(main)
    return main


def _dirs(tmp_path, monkeypatch):
    sess = tmp_path / ".sessions"
    sess.mkdir()
    monkeypatch.setattr(persistence, "SESSIONS_DIR", sess)
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path / "backups")
    return sess


def _valid_tarball(sess_content=b'{"id":"s9"}'):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        info = tarfile.TarInfo(name="s9.json")
        info.size = len(sess_content)
        t.addfile(info, io.BytesIO(sess_content))
    buf.seek(0)
    return buf.read()


def test_admin_backup_downloads_gzip(tmp_path, monkeypatch):
    sess = _dirs(tmp_path, monkeypatch)
    (sess / "s1.json").write_text('{"id":"s1"}', encoding="utf-8")
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, admin_token="atok")
    with TestClient(main.app) as c:
        r = c.get("/admin/backup", headers=_HDR)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/gzip")
    assert "attachment" in r.headers.get("content-disposition", "")


def test_admin_backup_disabled_without_token(tmp_path, monkeypatch):
    """No ADMIN_TOKEN set -> admin endpoints are 404 (can't leak cross-tenant
    data on an open LAN deploy)."""
    _dirs(tmp_path, monkeypatch)
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, admin_token=None)
    with TestClient(main.app) as c:
        r = c.get("/admin/backup")
    assert r.status_code == 404


def test_admin_backup_wrong_token_403(tmp_path, monkeypatch):
    _dirs(tmp_path, monkeypatch)
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, admin_token="atok")
    with TestClient(main.app) as c:
        r = c.get("/admin/backup", headers={"X-Admin-Token": "nope"})
    assert r.status_code == 403


def test_admin_restore_replaces_and_returns_safety(tmp_path, monkeypatch):
    sess = _dirs(tmp_path, monkeypatch)
    (sess / "old.json").write_text("x", encoding="utf-8")
    tarball = _valid_tarball()
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, admin_token="atok")
    with TestClient(main.app) as c:
        r = c.post("/admin/restore", headers=_HDR,
                   files={"file": ("b.tgz", tarball, "application/gzip")})
    assert r.status_code == 200
    body = r.json()
    assert body["restored"] is True and "safety_backup" in body
    assert (sess / "s9.json").exists() and not (sess / "old.json").exists()


def test_admin_restore_disabled_without_token(tmp_path, monkeypatch):
    _dirs(tmp_path, monkeypatch)
    tarball = _valid_tarball()
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, admin_token=None)
    with TestClient(main.app) as c:
        r = c.post("/admin/restore", files={"file": ("b.tgz", tarball, "application/gzip")})
    assert r.status_code == 404


def test_admin_restore_invalid_tar_400(tmp_path, monkeypatch):
    _dirs(tmp_path, monkeypatch)
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, admin_token="atok")
    with TestClient(main.app) as c:
        r = c.post("/admin/restore", headers=_HDR,
                   files={"file": ("b.tgz", b"not a tar", "application/gzip")})
    assert r.status_code == 400
