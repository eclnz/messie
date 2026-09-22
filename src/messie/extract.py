"""Pulling readable text out of files, cheaply.

Only ever reads the front of a file. Office formats are handled with the
standard library alone: .docx/.pptx/.xlsx/.epub are zip archives of XML, so
there is no need for a third-party parser.

Every extractor is best-effort. A file that cannot be read yields "" and the
caller falls back to the filename.
"""

from __future__ import annotations

import re
import zipfile
from html import unescape
from pathlib import Path

from messie.config import DEFAULT_SETTINGS, Settings
from messie.kinds import is_textual
from messie.scan import FileEntry

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# OOXML marks paragraph and cell boundaries; turn them into spaces, not nothing,
# so words from adjacent runs do not get glued together.
_BREAK_RE = re.compile(r"</(w:p|w:tab|a:p|text:p|p|div|br|li|tr|td)\b[^>]*>", re.IGNORECASE)
_RTF_CTRL_RE = re.compile(r"\\[a-z]+-?\d*\s?|[{}]", re.IGNORECASE)

#: Which member files inside each zip-based format actually hold prose.
_ZIP_MEMBERS: dict[str, tuple[str, ...]] = {
    "docx": ("word/document.xml", "word/header", "word/footnotes.xml"),
    "odt": ("content.xml",),
    "pptx": ("ppt/slides/slide", "ppt/notesSlides/notesSlide"),
    "odp": ("content.xml",),
    "xlsx": ("xl/sharedStrings.xml", "xl/worksheets/sheet1.xml"),
    "ods": ("content.xml",),
    "epub": (".xhtml", ".html", ".htm"),
}


def _clean(text: str, limit: int) -> str:
    text = _WS_RE.sub(" ", text).strip()
    return text[:limit]


def _strip_markup(xml: str) -> str:
    return unescape(_TAG_RE.sub("", _BREAK_RE.sub(" ", xml)))


def _from_zip_xml(path: Path, ext: str, limit: int) -> str:
    wanted = _ZIP_MEMBERS.get(ext, ())
    chunks: list[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            members = [n for n in names if any(n.startswith(w) or n.endswith(w) for w in wanted)]
            for member in sorted(members):
                try:
                    raw = zf.read(member).decode("utf-8", errors="replace")
                except (KeyError, OSError, zipfile.BadZipFile):
                    continue
                chunks.append(_strip_markup(raw))
                if sum(len(c) for c in chunks) >= limit:
                    break
    except (zipfile.BadZipFile, OSError):
        return ""
    return _clean(" ".join(chunks), limit)


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _from_plain(path: Path, limit: int, max_bytes: int) -> str:
    try:
        with path.open("rb") as fh:
            raw = fh.read(min(max_bytes, limit * 4))
    except OSError:
        return ""
    if b"\x00" in raw[:1024]:
        return ""  # binary masquerading as text
    return _clean(_decode(raw), limit)


def _from_rtf(path: Path, limit: int, max_bytes: int) -> str:
    raw = _from_plain(path, limit * 4, max_bytes)
    return _clean(_RTF_CTRL_RE.sub(" ", raw), limit)


def _from_html(path: Path, limit: int, max_bytes: int) -> str:
    raw = _from_plain(path, limit * 6, max_bytes)
    body = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    return _clean(_strip_markup(body), limit)


def _from_pdf(path: Path, limit: int) -> str:
    try:
        from pypdf import PdfReader
    except Exception:  # noqa: BLE001
        # Not just ImportError: pypdf pulls in compiled crypto backends, and a
        # mismatched one raises from native code at import time. A PDF reader
        # that cannot load is a missing feature, never a crash.
        return ""
    try:
        reader = PdfReader(str(path))
        chunks = []
        for page in reader.pages[:5]:
            chunks.append(page.extract_text() or "")
            if sum(len(c) for c in chunks) >= limit:
                break
        return _clean(" ".join(chunks), limit)
    except Exception:
        # pypdf raises a wide and version-dependent set of errors on damaged
        # files; an unreadable PDF is a fallback, not a crash.
        return ""


def _from_legacy_doc(path: Path, limit: int, max_bytes: int) -> str:
    """Salvage printable runs from a binary .doc. Rough, but better than nothing."""
    try:
        with path.open("rb") as fh:
            raw = fh.read(max_bytes)
    except OSError:
        return ""
    runs = re.findall(rb"[\x20-\x7e]{6,}", raw)
    text = " ".join(r.decode("ascii", errors="ignore") for r in runs)
    return _clean(text, limit)


def extract_text(entry: FileEntry, settings: Settings = DEFAULT_SETTINGS) -> str:
    """Readable text from a file, or "" if there is none to be had."""
    if not is_textual(entry.kind) or entry.size == 0:
        return ""

    ext, path = entry.ext, entry.path
    limit, max_bytes = settings.text_excerpt_chars, settings.max_read_bytes

    if ext in _ZIP_MEMBERS:
        return _from_zip_xml(path, ext, limit)
    if ext == "pdf":
        return _from_pdf(path, limit)
    if ext == "rtf":
        return _from_rtf(path, limit, max_bytes)
    if ext in {"html", "htm", "xhtml", "xml"}:
        return _from_html(path, limit, max_bytes)
    if ext in {"doc", "ppt", "xls"}:
        return _from_legacy_doc(path, limit, max_bytes)
    return _from_plain(path, limit, max_bytes)
