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
# Collapse runs of spaces and tabs, but keep newlines. Line structure is part
# of what a file says: a table is not prose, and flattening it loses that.
_WS_RE = re.compile(r"[^\S\n]+")
_BLANK_RE = re.compile(r"\n{3,}")
# OOXML marks paragraph and cell boundaries; turn them into spaces, not nothing,
# so words from adjacent runs do not get glued together.
_BREAK_RE = re.compile(r"</(w:p|a:p|text:p|p|div|li|tr)\b[^>]*>", re.IGNORECASE)
_INLINE_BREAK_RE = re.compile(r"</(w:tab|br|td|si)\b[^>]*>", re.IGNORECASE)
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
    text = _WS_RE.sub(" ", text)
    text = _BLANK_RE.sub("\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()[:limit]


def _strip_markup(xml: str) -> str:
    spaced = _INLINE_BREAK_RE.sub(" ", xml)
    return unescape(_TAG_RE.sub("", _BREAK_RE.sub("\n", spaced)))


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


#: RTF groups that hold machinery rather than prose. Their *contents* are
#: readable words — font and colour names, style names, the producing
#: application — so stripping control words alone leaves "Helvetica;" and
#: "Times New Roman;" sitting at the front of every document's text, where they
#: pollute the vector and make two unrelated files look slightly alike.
_RTF_MACHINERY = frozenset(
    {
        "fonttbl", "colortbl", "stylesheet", "info", "pict", "listtable",
        "listoverridetable", "rsidtbl", "generator", "themedata", "datastore",
        "latentstyles", "xmlnstbl", "filetbl", "revtbl",
    }
)


def _drop_rtf_groups(text: str) -> str:
    """Remove whole ``{\\fonttbl ...}`` style groups, braces and all."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "{":
            out.append(text[i])
            i += 1
            continue

        k = i + 1
        if k < n and text[k] == "\\":
            k += 1
            if k < n and text[k] == "*":
                k += 1
                if k < n and text[k] == "\\":
                    k += 1
            word = ""
            while k < n and text[k].isalpha():
                word += text[k]
                k += 1
            if word.lower() in _RTF_MACHINERY:
                depth = 0
                while i < n:  # skip to the matching close brace
                    if text[i] == "{":
                        depth += 1
                    elif text[i] == "}":
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _from_rtf(path: Path, limit: int, max_bytes: int) -> str:
    raw = _from_plain(path, limit * 4, max_bytes)
    return _clean(_RTF_CTRL_RE.sub(" ", _drop_rtf_groups(raw)), limit)


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
    """The prose inside a file, or "" if there is none to be had.

    Files with no prose in them — photographs, archives, fonts — are not this
    function's business. ``messie.metadata`` reads what their container says
    instead, and ``Engine._text_for`` is where the two are combined.
    """
    if entry.size == 0 or not is_textual(entry.kind):
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
