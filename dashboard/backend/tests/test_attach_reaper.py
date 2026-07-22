import os, time, tempfile
import main


def test_reaper_removes_old_attach_temps_only():
    old = tempfile.NamedTemporaryFile(prefix="wizattach-", suffix=".zip", delete=False)
    old.close()
    other = tempfile.NamedTemporaryFile(prefix="unrelated-", delete=False)
    other.close()
    past = time.time() - 10_000
    os.utime(old.name, (past, past)); os.utime(other.name, (past, past))
    main._reap_attach_temps(ttl_seconds=3600)
    assert not os.path.exists(old.name)      # our old temp reaped
    assert os.path.exists(other.name)        # unrelated temp untouched
    os.unlink(other.name)

def test_reaper_keeps_fresh_attach_temps():
    fresh = tempfile.NamedTemporaryFile(prefix="wizattach-", delete=False)
    fresh.close()
    main._reap_attach_temps(ttl_seconds=3600)
    assert os.path.exists(fresh.name)        # young temp kept
    os.unlink(fresh.name)
