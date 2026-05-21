"""Deterministic UUID and int-ID generation for wiz-builder.

UUIDs use uuid5 with a fixed namespace + manifest-hash-seeded input, so
re-compiling the same manifest produces the same UUIDs (important for
diffing and dashboard re-renders).

speechId is intentionally NON-deterministic — mirrors WIZ.AI's own
behavior where every export gets a fresh 16-digit speechId.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from uuid import UUID, uuid5

# Fixed namespace for wiz-builder. Never change this — UUIDs derived under
# a different namespace would not round-trip stably across versions.
_NAMESPACE = UUID("c1d9ef00-1357-4357-8123-456789abcdef")


@dataclass
class IdMinter:
    """Generate stable IDs from a manifest hash + seed string."""

    manifest_hash: str

    def uuid(self, seed: str) -> UUID:
        """Return a deterministic UUID5 derived from manifest_hash + seed."""
        full_seed = f"{self.manifest_hash}:{seed}"
        return uuid5(_NAMESPACE, full_seed)

    def int_id(self, seed: str) -> int:
        """Return a deterministic positive int < 2**31, derived from seed."""
        full_seed = f"{self.manifest_hash}:{seed}"
        digest = hashlib.sha256(full_seed.encode("utf-8")).digest()
        # Take 4 bytes, mask the high bit to keep it positive and inside int32.
        return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF or 1

    @staticmethod
    def random_speech_id() -> int:
        """Return a fresh 16-digit speechId (RNG-based; not deterministic)."""
        rng = random.SystemRandom()
        return rng.randint(10**15, 10**16 - 1)


def manifest_hash_of(text: str) -> str:
    """SHA-256 hex digest of a manifest's raw YAML text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
