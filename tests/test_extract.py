"""Text extraction, including Office formats via the standard library."""

from __future__ import annotations

import sys
import types
import zipfile
from pathlib import Path

import pytest
from conftest import write_blob, write_docx, write_text

from messie.config import DEFAULT_SETTINGS
from messie.extract import extract_text
from messie.scan import read_dir


def _entry(path: Path):
    return next(f for f in read_dir(path.parent).files if f.name == path.name)


def test_reads_a_real_docx(tmp_path: Path):
    path = write_docx(tmp_path / "report.docx", ["Quarterly revenue", "grew by eleven percent"])
    text = extract_text(_entry(path))
    assert "Quarterly revenue" in text
    assert "grew by eleven percent" in text


def test_docx_paragraphs_do_not_run_together(tmp_path: Path):
    path = write_docx(tmp_path / "a.docx", ["first", "second"])
    assert "firstsecond" not in extract_text(_entry(path))


def test_handles_a_corrupt_docx_without_raising(tmp_path: Path):
    path = tmp_path / "broken.docx"
    path.write_bytes(b"PK\x03\x04 this is not really a zip")
    assert extract_text(_entry(path)) == ""


def test_reads_plain_text_and_strips_whitespace(tmp_path: Path):
    path = write_text(tmp_path / "notes.md", "# Heading\n\n  spaced   out  \n")
    # Runs of spaces collapse, but line structure survives: it is what tells a
    # table apart from prose when judging whether text is legible at all.
    assert extract_text(_entry(path)) == "# Heading\n\nspaced out"


def test_decodes_non_utf8(tmp_path: Path):
    path = tmp_path / "latin.txt"
    path.write_bytes("café budget".encode("cp1252"))
    assert "budget" in extract_text(_entry(path))


@pytest.mark.parametrize(
    ("encoding", "bom"),
    [
        ("utf-16-le", False),
        ("utf-16-be", False),
        ("utf-16-le", True),
        ("utf-16-be", True),
    ],
)
def test_decodes_utf16_with_or_without_bom(
    tmp_path: Path, encoding: str, bom: bool
):
    path = tmp_path / f"utf16-{encoding}-{bom}.txt"
    payload = "UTF-16 report: café budget"
    raw = payload.encode(encoding)
    if bom:
        raw = (b"\xff\xfe" if encoding.endswith("le") else b"\xfe\xff") + raw
    path.write_bytes(raw)

    assert extract_text(_entry(path)) == payload


def test_binary_masquerading_as_text_yields_nothing(tmp_path: Path):
    path = tmp_path / "fake.txt"
    path.write_bytes(b"\x00\x01\x02binary\x00" * 50)
    assert extract_text(_entry(path)) == ""


def test_utf16_decoding_does_not_allow_decoded_nuls_from_binary(tmp_path: Path):
    path = tmp_path / "binary-utf16-looking.txt"
    # This has a UTF-16-like zero-byte pattern, but contains NUL code points
    # in the decoded value and must remain classified as binary.
    path.write_bytes(b"A\x00\x00\x00B\x00\x00\x00" * 30)

    assert extract_text(_entry(path)) == ""


def test_images_are_not_read(tmp_path: Path):
    path = write_blob(tmp_path / "photo.jpg")
    assert extract_text(_entry(path)) == ""


def test_empty_file_yields_nothing(tmp_path: Path):
    path = write_text(tmp_path / "empty.txt", "")
    assert extract_text(_entry(path)) == ""


def test_xlsx_shared_strings(tmp_path: Path):
    path = tmp_path / "budget.xlsx"
    shared = (
        '<?xml version="1.0"?><sst><si><t>Rent</t></si><si><t>Utilities</t></si></sst>'
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/sharedStrings.xml", shared)
    text = extract_text(_entry(path))
    assert "Rent" in text and "Utilities" in text


def test_xlsx_reads_all_worksheet_parts(tmp_path: Path):
    path = tmp_path / "multi-sheet.xlsx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            "<worksheet><row><c>First worksheet</c></row></worksheet>",
        )
        zf.writestr(
            "xl/worksheets/sheet2.xml",
            "<worksheet><row><c>Later worksheet</c></row></worksheet>",
        )
        zf.writestr(
            "xl/worksheets/_rels/sheet2.xml.rels",
            "<Relationships><Relationship>must not leak</Relationship>"
            "</Relationships>",
        )

    text = extract_text(_entry(path))
    assert "First worksheet" in text
    assert "Later worksheet" in text
    assert "must not leak" not in text


def test_xlsx_uses_one_cumulative_read_budget_across_sheets(tmp_path: Path):
    path = tmp_path / "budgeted-sheets.xlsx"
    first = "<worksheet><row><c>First sheet " + ("x" * 80) + "</c></row></worksheet>"
    second = "<worksheet><row><c>Second sheet marker</c></row></worksheet>"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/worksheets/sheet1.xml", first)
        zf.writestr("xl/worksheets/sheet2.xml", second)

    settings = DEFAULT_SETTINGS.with_(
        text_excerpt_chars=1000, max_read_bytes=len(first.encode("utf-8"))
    )
    text = extract_text(_entry(path), settings)
    assert "First sheet" in text
    assert "Second sheet marker" not in text


def test_excerpt_is_capped(tmp_path: Path):
    path = write_text(tmp_path / "long.txt", "word " * 50000)
    settings = DEFAULT_SETTINGS.with_(text_excerpt_chars=200)
    assert len(extract_text(_entry(path), settings)) <= 200


def test_zip_document_respects_read_budget(tmp_path: Path):
    path = tmp_path / "large.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            "<document>" + "x" * 10_000 + "beyond budget" + "</document>",
        )
    settings = DEFAULT_SETTINGS.with_(text_excerpt_chars=200, max_read_bytes=512)

    assert "beyond budget" not in extract_text(_entry(path), settings)


def test_pdf_larger_than_the_read_budget_is_not_parsed(tmp_path: Path, monkeypatch):
    path = tmp_path / "large.pdf"
    path.write_bytes(b"%PDF" + b"x" * 100)
    opened = False

    class Reader:
        def __init__(self, _stream):
            nonlocal opened
            opened = True

    module = types.ModuleType("pypdf")
    module.PdfReader = Reader
    monkeypatch.setitem(sys.modules, "pypdf", module)

    settings = DEFAULT_SETTINGS.with_(max_read_bytes=10)
    assert extract_text(_entry(path), settings) == ""
    assert not opened


def test_pdf_extraction_stops_after_two_pages(tmp_path: Path, monkeypatch):
    path = tmp_path / "many-pages.pdf"
    path.write_bytes(b"%PDF placeholder")
    visited: list[int] = []

    class Page:
        def __init__(self, number: int):
            self.number = number

        def extract_text(self):
            visited.append(self.number)
            return f"page {self.number}"

    class Reader:
        def __init__(self, _stream):
            self.pages = [Page(number) for number in range(5)]

    module = types.ModuleType("pypdf")
    module.PdfReader = Reader
    monkeypatch.setitem(sys.modules, "pypdf", module)

    assert extract_text(_entry(path)) == "page 0 page 1"
    assert visited == [0, 1]
