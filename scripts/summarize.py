import argparse
import sys
from pathlib import Path

# Make wizcheck importable
_HERE = Path(__file__).resolve().parent
_WIZCHECK_PATH = _HERE.parent / ".claude" / "skills" / "wiz-checker" / "scripts"
if str(_WIZCHECK_PATH) not in sys.path:
    sys.path.insert(0, str(_WIZCHECK_PATH))

from wizcheck.parser import parse_file, ParseError
from wizcheck.summarizer import build_markdown_summary

def main():
    parser = argparse.ArgumentParser(description="Summarize WIZ.AI exported JSON")
    parser.add_argument("file", help="Path to JSON")
    args = parser.parse_args()
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"summarize: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
        
    try:
        wf = parse_file(file_path)
    except ParseError as e:
        print(f"summarize: parse error: {e}", file=sys.stderr)
        sys.exit(1)
        
    summary = build_markdown_summary(wf)
    print("Summary:")
    print(summary)

if __name__ == "__main__":
    main()
