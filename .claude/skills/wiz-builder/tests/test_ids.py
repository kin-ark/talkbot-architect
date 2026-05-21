"""Tests for wizbuilder.ids — deterministic UUID + int generation."""

from __future__ import annotations

from uuid import UUID

from wizbuilder.ids import IdMinter


def test_uuid_for_same_input_is_stable():
    """Calling uuid(seed) twice on the same minter returns the same UUID."""
    minter = IdMinter(manifest_hash="abc123")
    u1 = minter.uuid("canvas:greeting")
    u2 = minter.uuid("canvas:greeting")
    assert u1 == u2
    assert isinstance(u1, UUID)


def test_uuid_for_different_seeds_differs():
    """Different seeds → different UUIDs."""
    minter = IdMinter(manifest_hash="abc123")
    assert minter.uuid("canvas:greeting") != minter.uuid("canvas:closing")


def test_uuid_for_different_manifest_hashes_differs():
    """Same seed string but different manifest hash → different UUIDs."""
    a = IdMinter(manifest_hash="abc123").uuid("canvas:greeting")
    b = IdMinter(manifest_hash="xyz789").uuid("canvas:greeting")
    assert a != b


def test_uuid_is_version_5():
    """Generated UUIDs use uuid5 (deterministic, namespace-based)."""
    minter = IdMinter(manifest_hash="abc123")
    u = minter.uuid("canvas:greeting")
    assert u.version == 5


def test_int_id_for_same_input_is_stable():
    """Deterministic positive int IDs (used for SpeechIntent.intentId, SpeechVariable.id)."""
    minter = IdMinter(manifest_hash="abc123")
    a = minter.int_id("variable:CLIENT_NAME")
    b = minter.int_id("variable:CLIENT_NAME")
    assert a == b
    assert a > 0


def test_int_id_for_different_seeds_differs():
    minter = IdMinter(manifest_hash="abc123")
    assert minter.int_id("variable:CLIENT_NAME") != minter.int_id("variable:DUE_AMOUNT")


def test_int_id_fits_in_int32():
    """IDs fit in a 32-bit signed int — WIZ.AI's IDs are smaller than 10**9 in observed data."""
    minter = IdMinter(manifest_hash="abc123")
    for seed in [f"variable:V{i}" for i in range(100)]:
        n = minter.int_id(seed)
        assert 0 < n < 2**31


def test_random_speech_id_is_16_digits():
    """speechId is random per build (mirrors WIZ.AI), 16 digits."""
    minter = IdMinter(manifest_hash="abc123")
    sid = minter.random_speech_id()
    assert 10**15 <= sid < 10**16


def test_random_speech_id_is_not_deterministic():
    """Distinct calls → distinct speech IDs (it's RNG-based, not hash-based)."""
    minter = IdMinter(manifest_hash="abc123")
    ids = {minter.random_speech_id() for _ in range(20)}
    assert len(ids) == 20  # 20 distinct values out of 20 calls
