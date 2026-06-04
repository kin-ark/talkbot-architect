"""Apply a sequence of mods to an InputBundle.

Reuses wiz-builder's IdMinter for any new-entity IDs. The wiz-builder scripts
dir is added to sys.path so `wizbuilder.ids` is importable as a sibling skill.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parents[2]
_WB_SCRIPTS = _SKILL_DIR.parent / "wiz-builder" / "scripts"
if str(_WB_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_WB_SCRIPTS))

from wizbuilder.ids import IdMinter  # noqa: E402

from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.registry import get_op  # noqa: E402


def run_mods(bundle: InputBundle, mods: list[dict], manifest_hash: str) -> None:
    """Apply each mod in order, mutating the bundle in place.

    Raises ValueError (from an op) if a target is missing; the caller decides
    whether to write. No write happens here.
    """
    minter = IdMinter(manifest_hash=manifest_hash)
    for i, entry in enumerate(mods):
        params = {k: v for k, v in entry.items() if k != "op"}
        op = get_op(entry["op"])
        try:
            op(bundle, params, minter)
        except (ValueError, KeyError) as e:
            raise ValueError(f"mod #{i + 1} ({entry['op']}): {e}") from e
