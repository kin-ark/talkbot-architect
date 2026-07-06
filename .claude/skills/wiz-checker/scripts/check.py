"""CLI entry point for wiz-checker.

Usage:
    python scripts/check.py <file.json> [--json] [--strict] [--deploy] [--only PREFIX]

Exit codes:
    0  clean (no errors; warnings allowed unless --strict)
    1  errors present; warnings under --strict; or deploy-blockers under --deploy
    2  reserved (in v1 collapses to 0)
    3  fatal parse error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the wizcheck package importable when running this script directly.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from wizcheck.checks import REGISTRY  # noqa: E402
from wizcheck.parser import ParseError, parse_file  # noqa: E402
from wizcheck.report import DEPLOY_BLOCKER_CODES, Report  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wiz-checker",
        description="Validate a WIZ.AI exported dialogue JSON file.",
    )
    p.add_argument("file", help="Path to WIZ.AI exported JSON file.")
    p.add_argument("--json", action="store_true",
                   help="Emit machine-readable JSON report to stdout.")
    p.add_argument("--strict", action="store_true",
                   help="Treat warnings as errors (exit 1 if any warning).")
    p.add_argument("--deploy", action="store_true",
                   help="Fail if any deploy-blocker (orphan / unreachable / missing-Exit / "
                        "unconnected Unclassified) is present — the pre-deploy readiness gate.")
    p.add_argument("--only", default=None,
                   help="Run only findings whose code starts with this prefix (e.g. WIZ1).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"wiz-checker: file not found: {file_path}", file=sys.stderr)
        return 3

    try:
        wf = parse_file(file_path)
    except ParseError as e:
        print(f"wiz-checker: parse error: {e}", file=sys.stderr)
        return 3

    if getattr(wf, "is_component_export", False):
        print(
            "note: component-export format detected — bot-scope checks "
            "(WIZ104/110/202/303) suppressed",
            file=sys.stderr,
        )

    report = Report(file=str(file_path), checks_run=list(REGISTRY.keys()))
    for _name, check_fn in REGISTRY.items():
        report.extend(check_fn(wf))

    if getattr(wf, "is_component_export", False):
        from wizcheck.component_adapter import BOT_SCOPE_CODES
        report.findings = [f for f in report.findings if f.code not in BOT_SCOPE_CODES]

    if args.only:
        report.findings = [f for f in report.findings if f.code.startswith(args.only)]

    if args.json:
        print(report.to_json_string())
    else:
        report.print_terminal()

    errors = report.error_count()
    warnings = report.warning_count()
    if errors > 0:
        return 1
    if args.strict and warnings > 0:
        return 1
    if args.deploy and any(f.code in DEPLOY_BLOCKER_CODES for f in report.findings):
        return 1
    return 0


if __name__ == "__main__":
    # Ensure UTF-8 output on Windows where stdout may default to cp1252.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
