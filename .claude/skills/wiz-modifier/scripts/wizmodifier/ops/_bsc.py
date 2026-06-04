"""Shared helpers for ops that read/write BizSpeechComponent entries."""

from __future__ import annotations

from wizmodifier import codec
from wizmodifier.io import InputBundle


def get_components(bundle: InputBundle) -> list[dict]:
    """Decode the BizSpeechComponent list."""
    raw = bundle.data.get("BizSpeechComponent")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("BizSpeechComponent is missing or empty")
    return codec.decode(raw)


def set_components(bundle: InputBundle, comps: list[dict]) -> None:
    """Re-encode and store the BizSpeechComponent list."""
    bundle.data["BizSpeechComponent"] = codec.encode(comps)


def require_component(comps: list[dict], index: int) -> dict:
    """Return comps[index] or raise a precise error."""
    if not isinstance(index, int) or index < 0 or index >= len(comps):
        noun = "entry" if len(comps) == 1 else "entries"
        raise ValueError(f"component {index} not found (file has {len(comps)} BSC {noun})")
    return comps[index]
