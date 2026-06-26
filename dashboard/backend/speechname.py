"""Read/write the bot display name (BizSpeechScene.speechName) in a WIZ export.

BizSpeechScene is an escaped-JSON string in real exports (the wire form the
builder emits) but a plain dict in *.unpacked.json dev files. This module is the
only place that decodes/encodes it. All functions are defensive — never raise.
"""
from __future__ import annotations

import copy
import json
import re


def _decode_scene(raw) -> tuple[dict, bool]:
    """Return (scene_dict, was_string). scene_dict is {} when undecodable."""
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
            return (obj, True) if isinstance(obj, dict) else ({}, True)
        except (json.JSONDecodeError, TypeError):
            return {}, True
    if isinstance(raw, dict):
        return raw, False
    return {}, False


def read_speech_name(data: dict) -> str | None:
    """Return BizSpeechScene.speechName, or None if absent/blank/malformed."""
    if not isinstance(data, dict):
        return None
    raw = data.get("BizSpeechScene")
    if raw is None:
        return None
    scene, _ = _decode_scene(raw)
    name = scene.get("speechName")
    return name if isinstance(name, str) and name.strip() else None


def set_speech_name(data: dict, name: str) -> dict:
    """Return a deep copy of *data* with speechName set, preserving the
    BizSpeechScene wire form (str stays str, dict stays dict). No-op (unchanged
    copy) when BizSpeechScene is absent or an undecodable string."""
    new = copy.deepcopy(data)
    raw = new.get("BizSpeechScene")
    if raw is None:
        return new
    scene, was_string = _decode_scene(raw)
    if not scene:
        return new
    scene["speechName"] = name
    new["BizSpeechScene"] = json.dumps(scene, ensure_ascii=False) if was_string else scene
    return new


def slugify_filename(name: str) -> str:
    """Turn a bot name into a safe '<slug>.json' filename; fallback default."""
    if not isinstance(name, str):
        name = ""
    slug = re.sub(r"\s+", "_", name.strip())
    slug = re.sub(r"[^A-Za-z0-9_-]", "", slug)
    return f"{slug}.json" if slug else "speech_export.json"
