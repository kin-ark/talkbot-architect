"""Decode WIZ manual text extracted by `pdftotext -layout`.

The embedded font maps each glyph to its true character minus 31 (0x1F),
so adding 31 to every printable byte in [0x21, 0x5F] restores the text.
Spaces, newlines, and bytes outside that range pass through unchanged.

Usage:
    pdftotext -layout "Manual.pdf" raw.txt
    python decode_pdf.py raw.txt decoded.txt
"""
from __future__ import annotations

import sys


def decode_text(s: str) -> str:
    out = []
    for c in s:
        n = ord(c)
        out.append(chr(n + 31) if 0x21 <= n <= 0x5F else c)
    return "".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: decode_pdf.py <in.txt> <out.txt>", file=sys.stderr)
        return 2
    src, dst = argv[1], argv[2]
    with open(src, encoding="utf-8", errors="replace") as f:
        text = f.read()
    with open(dst, "w", encoding="utf-8") as f:
        f.write(decode_text(text))
    print(f"decoded {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
