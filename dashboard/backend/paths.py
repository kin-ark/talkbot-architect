"""Single source of truth for importing the four skills' packages."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILLS = _REPO_ROOT / ".claude" / "skills"
_SCRIPT_DIRS = [
    _SKILLS / "wiz-checker" / "scripts",
    _SKILLS / "wiz-modifier" / "scripts",
    _SKILLS / "wiz-builder" / "scripts",
    _SKILLS / "wiz-facts" / "scripts",
]


def add_skill_paths() -> None:
    for d in _SCRIPT_DIRS:
        s = str(d)
        if s not in sys.path:
            sys.path.insert(0, s)


def repo_root() -> Path:
    return _REPO_ROOT


def skills_dir() -> Path:
    """Return the root of the .claude/skills directory."""
    return _SKILLS
