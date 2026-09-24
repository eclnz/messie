"""Text extraction, including Office formats via the standard library."""

from __future__ import annotations

import sys
import types
import zipfile
from pathlib import Path

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


def test_binary_masquerading_as_text_yields_nothing(tmp_path: Path):
    path = tmp_path / "fake.txt"
    path.write_bytes(b"\x00\x01\x02binary\x00" * 50)
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


def test_pdf_parser_receives_a_bounded_reader(tmp_path: Path, monkeypatch):
    path = tmp_path / "large.pdf"
    path.write_bytes(b"%PDF" + b"x" * 100)
    reads: list[int] = []

    class Reader:
        def __init__(self, stream):
            reads.append(len(stream.read(100)))
            reads.append(len(stream.read(100)))
            self.pages = []

    module = types.ModuleType("pypdf")
    module.PdfReader = Reader
    monkeypatch.setitem(sys.modules, "pypdf", module)

    settings = DEFAULT_SETTINGS.with_(max_read_bytes=10)
    assert extract_text(_entry(path), settings) == ""
    assert sum(reads) == 10
