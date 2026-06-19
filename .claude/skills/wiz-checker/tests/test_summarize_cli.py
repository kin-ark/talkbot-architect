import subprocess
import sys
from pathlib import Path

def test_cli_help():
    # We execute scripts/summarize.py from the root of the repo
    root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    script_path = root_dir / "scripts" / "summarize.py"
    
    result = subprocess.run([sys.executable, str(script_path), "-h"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Summarize WIZ.AI exported JSON" in result.stdout

def test_cli_valid_json():
    root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    script_path = root_dir / "scripts" / "summarize.py"
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "minimal_valid.json"
    
    result = subprocess.run([sys.executable, str(script_path), str(fixture_path)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Summary:" in result.stdout

def test_cli_missing_file():
    root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    script_path = root_dir / "scripts" / "summarize.py"
    
    result = subprocess.run([sys.executable, str(script_path), "non_existent.json"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "file not found" in result.stderr

def test_cli_parse_error():
    root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    script_path = root_dir / "scripts" / "summarize.py"
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "malformed_uuid.json"
    
    result = subprocess.run([sys.executable, str(script_path), str(fixture_path)], capture_output=True, text=True)
    # The malformed_uuid.json has schema validation errors, which the parser throws as ParseError.
    assert result.returncode == 1
    assert "parse error" in result.stderr
