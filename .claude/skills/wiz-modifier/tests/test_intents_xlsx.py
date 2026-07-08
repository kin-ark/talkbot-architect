from pathlib import Path

import pytest

from wizmodifier.xlsx import read_rows, write_sheet


def test_write_then_read_roundtrip(tmp_path):
    # write to an .xls-named path (WIZ's quirk: xlsx bytes, .xls extension)
    p = tmp_path / "out.xls"
    write_sheet(p, ["Intent", "Type", "Content", "Language"],
                [["Positive", "Keyword", "ya", "Bahasa Indonesia"]],
                note="Note: test")
    rows = read_rows(p)
    # note row, header row, data row
    assert rows[0][0].startswith("Note")
    assert rows[1] == ["Intent", "Type", "Content", "Language"]
    assert rows[2] == ["Positive", "Keyword", "ya", "Bahasa Indonesia"]


def test_read_bytesio_bypasses_xls_extension(tmp_path):
    # write_sheet writes real xlsx bytes; naming it .xls must still read (BytesIO).
    p = tmp_path / "sheet.xls"
    write_sheet(p, ["A"], [["x"]])
    rows = read_rows(p)
    assert rows[-1] == ["x"]


def test_read_missing_file_raises(tmp_path):
    with pytest.raises(ValueError):
        read_rows(tmp_path / "nope.xls")
