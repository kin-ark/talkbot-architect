import io
import importlib
import tarfile
import persistence
import backup


def _reload_main(monkeypatch, password):
    if password is None:
        monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("DASHBOARD_PASSWORD", password)
    import main, auth
    importlib.reload(auth)
    importlib.reload(main)
    return main


def _dirs(tmp_path, monkeypatch):
    sess = tmp_path / ".sessions"; sess.mkdir()
    monkeypatch.setattr(persistence, "SESSIONS_DIR", sess)
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path / "backups")
    return sess


def _valid_tarball(sess_content=b'{"id":"s9"}'):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        info = tarfile.TarInfo(name="s9.json"); info.size = len(sess_content)
        t.addfile(info, io.BytesIO(sess_content))
    buf.seek(0)
    return buf.read()


def test_admin_backup_downloads_gzip(tmp_path, monkeypatch):
    sess = _dirs(tmp_path, monkeypatch)
    (sess / "s1.json").write_text('{"id":"s1"}', encoding="utf-8")
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, "secret")
    with TestClient(main.app) as c:
        r = c.get("/admin/backup", auth=("admin", "secret"))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/gzip")
    assert "attachment" in r.headers.get("content-disposition", "")


def test_admin_restore_replaces_and_returns_safety(tmp_path, monkeypatch):
    sess = _dirs(tmp_path, monkeypatch)
    (sess / "old.json").write_text("x", encoding="utf-8")
    tarball = _valid_tarball()
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, "secret")
    with TestClient(main.app) as c:
        r = c.post("/admin/restore", auth=("admin", "secret"),
                   files={"file": ("b.tgz", tarball, "application/gzip")})
    assert r.status_code == 200
    body = r.json()
    assert body["restored"] is True and "safety_backup" in body
    assert (sess / "s9.json").exists() and not (sess / "old.json").exists()


def test_admin_restore_requires_password(tmp_path, monkeypatch):
    _dirs(tmp_path, monkeypatch)
    tarball = _valid_tarball()
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, None)          # no DASHBOARD_PASSWORD
    with TestClient(main.app) as c:
        r = c.post("/admin/restore", files={"file": ("b.tgz", tarball, "application/gzip")})
    assert r.status_code == 403


def test_admin_restore_invalid_tar_400(tmp_path, monkeypatch):
    _dirs(tmp_path, monkeypatch)
    from fastapi.testclient import TestClient
    main = _reload_main(monkeypatch, "secret")
    with TestClient(main.app) as c:
        r = c.post("/admin/restore", auth=("admin", "secret"),
                   files={"file": ("b.tgz", b"not a tar", "application/gzip")})
    assert r.status_code == 400
