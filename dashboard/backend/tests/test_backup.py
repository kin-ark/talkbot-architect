import io
import tarfile
import pytest
import persistence
import backup


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    sess = tmp_path / ".sessions"
    bdir = tmp_path / "backups"
    sess.mkdir()
    monkeypatch.setattr(persistence, "SESSIONS_DIR", sess)
    monkeypatch.setattr(backup, "BACKUP_DIR", bdir)
    return sess, bdir


def _seed(sess, name="s1.json", body='{"id":"s1"}'):
    (sess / name).write_text(body, encoding="utf-8")


def test_make_backup_contains_session_files(dirs):
    sess, bdir = dirs
    _seed(sess)
    (sess / "active.alice").write_text("s1", encoding="utf-8")
    path = backup.make_backup()
    assert path.endswith(".tgz")
    with tarfile.open(path) as t:
        names = t.getnames()
    assert "s1.json" in names and "active.alice" in names


def test_make_backup_empty_dir_ok(dirs):
    path = backup.make_backup()          # empty .sessions -> valid tar, no raise
    with tarfile.open(path) as t:
        assert t.getnames() == [] or all(n in (".", "") for n in t.getnames())


def test_open_backup_stream(dirs):
    sess, _ = dirs
    _seed(sess)
    data, filename = backup.open_backup_stream()
    assert isinstance(data, bytes) and len(data) > 0
    assert filename.startswith("sessions-") and filename.endswith(".tgz")


def test_restore_round_trip_and_safety(dirs):
    sess, bdir = dirs
    _seed(sess, body='{"id":"s1","v":1}')
    snap = backup.make_backup(prefix="manual")
    (sess / "s1.json").write_text('{"id":"s1","v":2}', encoding="utf-8")   # modify
    (sess / "junk.json").write_text("x", encoding="utf-8")                  # extra
    result = backup.restore_from(snap)
    assert result["restored"] is True
    assert "pre-restore" in result["safety_backup"]
    assert (sess / "s1.json").read_text(encoding="utf-8") == '{"id":"s1","v":1}'   # rolled back
    assert not (sess / "junk.json").exists()                                        # wiped
    assert any(p.name.startswith("pre-restore-") for p in bdir.glob("*.tgz"))


def test_restore_rejects_path_traversal(dirs):
    sess, _ = dirs
    _seed(sess)
    # hand-build a malicious tar with a ../ member
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        info = tarfile.TarInfo(name="../evil.json")
        payload = b"pwned"
        info.size = len(payload)
        t.addfile(info, io.BytesIO(payload))
    buf.seek(0)
    with pytest.raises(ValueError):
        backup.restore_from(buf)
    assert (sess / "s1.json").exists()                 # untouched
    assert not (sess.parent / "evil.json").exists()


def test_restore_rejects_non_tar(dirs):
    with pytest.raises(ValueError):
        backup.restore_from(io.BytesIO(b"not a tarball"))


def test_rotate_keeps_newest(dirs):
    _, bdir = dirs
    bdir.mkdir(parents=True, exist_ok=True)
    for ts in ("20260101T000000Z", "20260102T000000Z", "20260103T000000Z"):
        (bdir / f"auto-{ts}.tgz").write_text("x", encoding="utf-8")
    backup.rotate(keep=2)
    left = sorted(p.name for p in bdir.glob("auto-*.tgz"))
    assert left == ["auto-20260102T000000Z.tgz", "auto-20260103T000000Z.tgz"]


def test_start_scheduler_disabled_and_idempotent(monkeypatch):
    monkeypatch.setenv("BACKUP_INTERVAL_H", "0")
    backup._started = False
    backup.start_scheduler()                # disabled -> no thread
    assert backup._started is False
    monkeypatch.setenv("BACKUP_INTERVAL_H", "6")
    backup._started = False
    backup.start_scheduler()
    assert backup._started is True
    backup.start_scheduler()                # idempotent (no crash / second thread)
    assert backup._started is True
