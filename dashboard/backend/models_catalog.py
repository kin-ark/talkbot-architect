"""Curated, env-extendable LLM model catalog for the dashboard.

The dashboard shows a fixed dropdown of models; each entry carries the
provider + exact model string + optional base_url so picking one entry
configures everything (the user supplies only an API key). DeepSeek and
similar hosts ride the Anthropic-compatible API (provider "anthropic" +
a base_url override).

Env extension (both optional, applied at load):
- LLM_MODELS_JSON  — inline JSON array of entry dicts.
- LLM_MODELS_FILE  — path to a JSON array of entry dicts.
Entries append to the built-in list; an id collision overrides the built-in.
Malformed override → logged warning + built-in catalog only (never crashes).
- LLM_DEFAULT_MODEL_ID — overrides the default entry id (must match a loaded
  id, else the built-in default stands).
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

log = logging.getLogger("dashboard.catalog")


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    label: str
    provider: str
    model: str
    base_url: str | None
    group: str
    vision: bool = True


_BUILTIN: list[CatalogEntry] = [
    CatalogEntry("claude-opus-4-8", "Claude Opus 4.8", "anthropic",
                 "claude-opus-4-8", None, "Claude"),
    CatalogEntry("claude-sonnet-5", "Claude Sonnet 5", "anthropic",
                 "claude-sonnet-5", None, "Claude"),
    CatalogEntry("claude-haiku-4-5", "Claude Haiku 4.5", "anthropic",
                 "claude-haiku-4-5-20251001", None, "Claude"),
]

_BUILTIN_DEFAULT = "claude-opus-4-8"

CUSTOM_MODEL_ID = "__custom__"
PROVIDERS = ["anthropic", "openai", "openai-compatible"]


def _coerce_entries(raw) -> list[CatalogEntry]:
    out: list[CatalogEntry] = []
    if not isinstance(raw, list):
        raise ValueError("catalog override must be a JSON array")
    for d in raw:
        out.append(CatalogEntry(
            id=str(d["id"]), label=str(d.get("label", d["id"])),
            provider=str(d.get("provider", "anthropic")),
            model=str(d["model"]),
            base_url=(d.get("base_url") or None),
            group=str(d.get("group", "Custom")),
            vision=bool(d.get("vision", True)),
        ))
    return out


def _overrides() -> list[CatalogEntry]:
    text = None
    if os.environ.get("LLM_MODELS_JSON"):
        text = os.environ["LLM_MODELS_JSON"]
    elif os.environ.get("LLM_MODELS_FILE"):
        try:
            with open(os.environ["LLM_MODELS_FILE"], encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            log.warning("LLM_MODELS_FILE unreadable: %s", e)
            return []
    if not text:
        return []
    try:
        return _coerce_entries(json.loads(text))
    except (ValueError, KeyError, TypeError) as e:
        log.warning("ignoring malformed model catalog override: %s", e)
        return []


def load_catalog() -> list[CatalogEntry]:
    by_id: dict[str, CatalogEntry] = {e.id: e for e in _BUILTIN}
    order: list[str] = [e.id for e in _BUILTIN]
    for e in _overrides():
        if e.id not in by_id:
            order.append(e.id)
        by_id[e.id] = e
    return [by_id[i] for i in order]


def entry_by_id(entry_id: str | None) -> CatalogEntry | None:
    if not entry_id:
        return None
    for e in load_catalog():
        if e.id == entry_id:
            return e
    return None


def default_entry_id() -> str:
    override = os.environ.get("LLM_DEFAULT_MODEL_ID")
    if override and entry_by_id(override) is not None:
        return override
    return _BUILTIN_DEFAULT
