#!/usr/bin/env python3
"""CLI entry: modify a WIZ.AI export, or generate the import-test matrix.

Usage:
    python modify.py --mods <mods.yaml> [--force] [--no-check]
    python modify.py --preset <name> --in <json|zip> --out <dir> [--force] [--no-check]

For the import-test matrix, prefer a ZIP input (e.g. talkbot/Empty+Dialogue.zip)
so the WAV is carried into T0-T10 and T11 (zip-no-wav) is a meaningful test.

Exit codes:
    0  Success
    2  Bad input (invalid mod-manifest, unknown op, target not found)
    3  Output path conflict (use --force)
    4  Internal error
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from wizmodifier.apply import run_mods, run_preset  # noqa: E402
from wizmodifier.io import InputBundle, write_output  # noqa: E402
from wizmodifier.mods import ModManifestError, load_mods  # noqa: E402

_PROJECT_ROOT = _SCRIPTS_DIR.parents[3]
_CHECKER_CLI = _PROJECT_ROOT / ".claude" / "skills" / "wiz-checker" / "scripts" / "check.py"


def _advisory_check(json_path: Path) -> None:
    """Run wiz-checker and print its findings; never blocks or deletes output."""
    proc = subprocess.run(
        [sys.executable, str(_CHECKER_CLI), str(json_path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if proc.stdout.strip():
        print("--- wiz-checker (advisory) ---")
        print(proc.stdout)
    if proc.stderr.strip():
        print(proc.stderr, file=sys.stderr)


def _run_mods_manifest(args) -> int:
    try:
        manifest = load_mods(args.mods)
    except ModManifestError as e:
        print(f"mod-manifest error: {e}", file=sys.stderr)
        return 2

    out_path = Path(manifest.output_path)
    if out_path.exists() and not args.force:
        print(f"output {out_path} exists (use --force)", file=sys.stderr)
        return 3

    try:
        bundle = InputBundle.load(Path(manifest.input))
        if manifest.wav and not bundle.wavs:
            wav_path = Path(manifest.wav)
            bundle.wavs[wav_path.name] = wav_path.read_bytes()
        run_mods(bundle, manifest.mods, manifest_hash=manifest.input)
        write_output(bundle, out_path, fmt=manifest.output_format)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 4

    print(f"wrote {out_path}")
    if not args.no_check and manifest.output_format == "json":
        _advisory_check(out_path)
    return 0


def _run_preset(args) -> int:
    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        print(f"output dir {out_dir} not empty (use --force)", file=sys.stderr)
        return 3
    try:
        base = InputBundle.load(Path(args.in_path))
        written = run_preset(base, args.preset, out_dir, manifest_hash=str(args.in_path))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 4
    print(f"wrote {len(written)} files to {out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Modify a WIZ.AI export or build the import-test matrix."
    )
    p.add_argument("--mods", type=Path, help="Path to a mod-manifest YAML")
    p.add_argument("--preset", type=str, help="Preset name (e.g. import-test-matrix)")
    p.add_argument("--in", dest="in_path", type=Path, help="Input json|zip (preset mode)")
    p.add_argument("--out", type=Path, help="Output dir (preset mode)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-check", action="store_true", help="Skip the advisory checker")
    args = p.parse_args(argv)

    if args.preset:
        if not args.in_path or not args.out:
            print("--preset requires --in and --out", file=sys.stderr)
            return 2
        return _run_preset(args)
    if args.mods:
        return _run_mods_manifest(args)
    print("nothing to do: pass --mods or --preset", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
