"""Decode/encode the JSON-encoded string values that fill a WIZ speech*.json.

Every top-level value in a WIZ export (except kbTag) is itself a JSON string.
This module is the single source of truth for how wiz-modifier reads and
re-writes those strings — always compact, always UTF-8 preserving — so the
modifier never becomes a fidelity variable.
"""

from __future__ import annotations

import json
from typing import Any


def encode(value: Any) -> str:
    """Serialize a Python value to a compact JSON string (WIZ format)."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def decode(raw: str) -> Any:
    """Parse a JSON-encoded string value back to a Python value."""
    return json.loads(raw)
