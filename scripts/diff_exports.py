#!/usr/bin/env python3
"""Structural diff between two WIZ.AI exports.

Usage:
    python scripts/diff_exports.py <path-A> <path-B> [--focus FIELD ...]
"""
from __future__ import annotations
import argparse
import json
import zipfile
from pathlib import Path


def load_export(path: Path) -> dict:
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            speech = [n for n in names if Path(n).name.startswith("speech") and n.endswith(".json")]
            if len(speech) != 1:
                raise ValueError(f"expected 1 speech*.json in {path.name}, found {speech}")
            return json.loads(z.read(speech[0]).decode("utf-8"))
    return json.loads(path.read_text("utf-8"))


def normalize_speech_ids(obj):
    if isinstance(obj, dict):
        return {k: (0 if k == "speechId" else normalize_speech_ids(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_speech_ids(i) for i in obj]
    return obj


def decode_field(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def _diff_field(label: str, va, vb) -> list[str]:
    lines = []
    va_dec = decode_field(va)
    vb_dec = decode_field(vb)
    if isinstance(va_dec, list) and isinstance(vb_dec, list):
        match = "✓" if len(va_dec) == len(vb_dec) else "✗ MISMATCH"
        lines.append(f"  {label:<35} A:{len(va_dec):4}  B:{len(vb_dec):4}  {match}")
        if va_dec and vb_dec and isinstance(va_dec[0], dict) and isinstance(vb_dec[0], dict):
            ka, kb = set(va_dec[0]), set(vb_dec[0])
            only_a, only_b = ka - kb, kb - ka
            if only_a:
                lines.append(f"    entry[0] only in A: {sorted(only_a)}")
            if only_b:
                lines.append(f"    entry[0] only in B: {sorted(only_b)}")
    else:
        match = "✓" if normalize_speech_ids(va_dec) == normalize_speech_ids(vb_dec) else "✗ MISMATCH"
        lines.append(f"  {label:<35} {match}")
    return lines


def diff_exports(a: dict, b: dict, focus: list[str] | None = None) -> None:
    keys = focus if focus else list(dict.fromkeys(list(a.keys()) + list(b.keys())))
    print(f"  {'Field':<35} Result")
    print(f"  {'-'*60}")
    for k in keys:
        if k not in a:
            print(f"  {k:<35} MISSING IN A")
        elif k not in b:
            print(f"  {k:<35} MISSING IN B")
        else:
            for line in _diff_field(k, a[k], b[k]):
                print(line)


def main(argv=None):
    p = argparse.ArgumentParser(description="Structural diff between two WIZ.AI exports")
    p.add_argument("a", type=Path, metavar="PATH_A")
    p.add_argument("b", type=Path, metavar="PATH_B")
    p.add_argument("--focus", nargs="*", metavar="FIELD")
    args = p.parse_args(argv)
    diff_exports(load_export(args.a), load_export(args.b), args.focus)


if __name__ == "__main__":
    main()
