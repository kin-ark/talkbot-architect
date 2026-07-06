"""Corpus-derived bot-building playbooks (domain knowledge for the chat agent)."""
from __future__ import annotations

import re
from pathlib import Path

PLAYBOOKS_DIR = Path(__file__).parent

_SAFE = re.compile(r"^[a-z0-9_]+$")


def _title_of(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return fallback


def list_playbooks() -> list[dict]:
    out = []
    for p in sorted(PLAYBOOKS_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        out.append({"id": p.stem, "title": _title_of(text, p.stem)})
    return out


def get_playbook(vertical: str) -> str | None:
    """Return the playbook markdown for *vertical*, or None. Traversal-safe:
    only a bare [a-z0-9_] stem maps to a <stem>.md in this directory."""
    if not isinstance(vertical, str) or not _SAFE.match(vertical):
        return None
    p = PLAYBOOKS_DIR / f"{vertical}.md"
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8")
