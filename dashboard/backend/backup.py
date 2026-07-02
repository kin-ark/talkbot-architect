"""Backup/restore of the .sessions/ data dir. stdlib-only; never crashes the app.

Backups live in BACKUP_DIR (a SEPARATE volume from SESSIONS_DIR) so they neither
tar themselves nor get wiped on restore.
"""
from __future__ import annotations

import os
import tarfile
import tempfile
import threading
import time

import persistence
from logging_setup import log

BACKUP_DIR = os.environ.get("BACKUP_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")

_started = False
_SKIP_DIRS = {"backups", "logs"}


def _ts() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _sessions_dir() -> str:
    return str(persistence.SESSIONS_DIR)


def _add_sessions(tar: tarfile.TarFile) -> None:
    root = _sessions_dir()
    if not os.path.isdir(root):
        return
    for entry in sorted(os.listdir(root)):
        if entry.endswith(".tmp") or entry in _SKIP_DIRS:
            continue
        tar.add(os.path.join(root, entry), arcname=entry)   # arcname relative → unpacks flat


def make_backup(dest_dir: str | None = None, prefix: str = "auto") -> str:
    dest = dest_dir or BACKUP_DIR
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, f"{prefix}-{_ts()}.tgz")
    tmp = path + ".tmp"
    with tarfile.open(tmp, "w:gz") as tar:
        _add_sessions(tar)
    os.replace(tmp, path)
    return path


def open_backup_stream() -> tuple[bytes, str]:
    fd, tmp = tempfile.mkstemp(suffix=".tgz")
    os.close(fd)
    try:
        with tarfile.open(tmp, "w:gz") as tar:
            _add_sessions(tar)
        with open(tmp, "rb") as f:
            data = f.read()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    return data, f"sessions-{_ts()}.tgz"


def _is_safe_member(m: tarfile.TarInfo) -> bool:
    name = m.name
    if name.startswith("/") or os.path.isabs(name) or (os.path.splitdrive(name)[0]):
        return False
    parts = name.replace("\\", "/").split("/")
    if ".." in parts:
        return False
    return m.isfile() or m.isdir()          # no symlink/hardlink/dev/fifo


def _wipe_sessions() -> None:
    root = _sessions_dir()
    if not os.path.isdir(root):
        os.makedirs(root, exist_ok=True)
        return
    import shutil
    for entry in os.listdir(root):
        p = os.path.join(root, entry)
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.unlink(p)
            except OSError:
                pass


def restore_from(src) -> dict:
    safety = make_backup(prefix="pre-restore")
    try:
        if hasattr(src, "read"):
            tar = tarfile.open(fileobj=src, mode="r:*")
        else:
            tar = tarfile.open(src, mode="r:*")
    except (tarfile.ReadError, OSError) as e:
        raise ValueError(f"not a readable tar archive: {e}") from e
    with tar:
        members = tar.getmembers()
        for m in members:
            if not _is_safe_member(m):
                raise ValueError(f"unsafe tar member: {m.name}")
        _wipe_sessions()
        tar.extractall(_sessions_dir(), members=members)
    return {"restored": True, "safety_backup": safety}


def rotate(dest_dir: str | None = None, prefix: str = "auto", keep: int = 7) -> None:
    dest = dest_dir or BACKUP_DIR
    if not os.path.isdir(dest):
        return
    files = sorted(f for f in os.listdir(dest) if f.startswith(f"{prefix}-") and f.endswith(".tgz"))
    for f in files[:-keep] if keep > 0 else files:
        try:
            os.unlink(os.path.join(dest, f))
        except OSError:
            pass


def start_scheduler() -> None:
    global _started
    if _started:
        return
    try:
        interval_h = float(os.environ.get("BACKUP_INTERVAL_H", "6"))
    except ValueError:
        interval_h = 6.0
    if interval_h <= 0:
        return
    try:
        keep = int(os.environ.get("BACKUP_KEEP", "7"))
    except ValueError:
        keep = 7

    def _loop():
        while True:
            time.sleep(interval_h * 3600)       # sleep FIRST → no backup storm on restart
            try:
                t0 = time.perf_counter()
                path = make_backup(prefix="auto")
                rotate(keep=keep)
                log.info("", extra={"ev": "backup", "kind": "auto", "path": path,
                                    "ms": round((time.perf_counter() - t0) * 1000)})
            except Exception as e:              # one failure must not kill the thread
                log.error("", extra={"ev": "backup_error", "err": str(e)}, exc_info=e)

    threading.Thread(target=_loop, daemon=True, name="backup-scheduler").start()
    _started = True
