"""Best-effort text extraction."""

from __future__ import annotations

import logging
import re
import zipfile
from html import unescape
from pathlib import Path

from messie.config import DEFAULT_SETTINGS, Settings
from messie.kinds import is_textual
from messie.scan import FileEntry

_TAG_RE = re.compile(r"<[^>]+>")
# Keep newlines while normalising inline whitespace.
_WS_RE = re.compile(r"[^\S\n]+")
_BLANK_RE = re.compile(r"\n{3,}")
# Preserve markup boundaries between adjacent words.
_BREAK_RE = re.compile(r"</(w:p|a:p|text:p|p|div|li|tr)\b[^>]*>", re.IGNORECASE)
_INLINE_BREAK_RE = re.compile(r"</(w:tab|br|td|si)\b[^>]*>", re.IGNORECASE)
_RTF_CTRL_RE = re.compile(r"\\[a-z]+-?\d*\s?|[{}]", re.IGNORECASE)
_MIN_XML_READ = 16 << 10
_XML_READ_FACTOR = 12
_MAX_PDF_PAGES = 2

#: Which member files inside each zip-based format actually hold prose.
_ZIP_MEMBERS: dict[str, tuple[str, ...]] = {
    "docx": ("word/document.xml", "word/header", "word/footnotes.xml"),
    "odt": ("content.xml",),
    "pptx": ("ppt/slides/slide", "ppt/notesSlides/notesSlide"),
    "odp": ("content.xml",),
    # Worksheet parts are numbered by Excel (sheet1.xml, sheet2.xml, ...).
    # Keep the directory prefix here; _zip_member_matches restricts it to
    # direct worksheet XML parts and therefore excludes worksheet rels.
    "xlsx": ("xl/sharedStrings.xml", "xl/worksheets/"),
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


def _zip_member_matches(name: str, ext: str, wanted: tuple[str, ...]) -> bool:
    """Return whether *name* is a prose-bearing member of an archive."""
    if ext == "xlsx" and name.startswith("xl/worksheets/"):
        # Do not accidentally read worksheet relationship files or nested
        # metadata as prose.  Excel worksheet parts are direct XML children.
        remainder = name.removeprefix("xl/worksheets/")
        return "/" not in remainder and remainder.endswith(".xml")
    return any(name.startswith(prefix) or name.endswith(prefix) for prefix in wanted)


def _from_zip_xml(path: Path, ext: str, limit: int, max_bytes: int) -> str:
    wanted = _ZIP_MEMBERS.get(ext, ())
    chunks: list[str] = []
    remaining = max(0, max_bytes)
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            members = [n for n in names if _zip_member_matches(n, ext, wanted)]
            for member in sorted(members):
                if remaining == 0:
                    break
                try:
                    wanted_bytes = max(
                        _MIN_XML_READ,
                        (limit - sum(map(len, chunks))) * _XML_READ_FACTOR,
                    )
                    read_size = min(remaining, wanted_bytes)
                    with zf.open(member) as source:
                        data = source.read(read_size)
                    remaining -= len(data)
                    raw = data.decode("utf-8", errors="replace")
                except (KeyError, OSError, zipfile.BadZipFile):
                    continue
                chunks.append(_strip_markup(raw))
                if sum(len(c) for c in chunks) >= limit:
                    break
    except (zipfile.BadZipFile, OSError):
        return ""
    return _clean(" ".join(chunks), limit)


def _looks_like_utf16(raw: bytes) -> str | None:
    """Infer BOM-free UTF-16 from its characteristic zero-byte pattern.

    A BOM is preferred and handled by the caller.  Without one, ordinary
    prose encoded as UTF-16 has a zero byte in one position of most two-byte
    code units.  Requiring several matching units avoids classifying normal
    binary data with one or two NULs as text.
    """
    sample = raw[:1024]
    pair_count = len(sample) // 2
    if pair_count < 4:
        return None
    sample = sample[: pair_count * 2]
    le_zeros = sum(sample[index + 1] == 0 for index in range(0, len(sample), 2))
    be_zeros = sum(sample[index] == 0 for index in range(0, len(sample), 2))
    threshold = max(4, int(pair_count * 0.60))
    if le_zeros >= threshold and le_zeros > be_zeros:
        return "utf-16-le"
    if be_zeros >= threshold and be_zeros > le_zeros:
        return "utf-16-be"
    return None


def _decode_with_encoding(raw: bytes) -> tuple[str, bool]:
    """Decode bytes and report whether UTF-16 handling was selected."""
    if raw.startswith(b"\xff\xfe"):
        try:
            return raw.decode("utf-16-le").lstrip("\ufeff"), True
        except UnicodeDecodeError:
            pass
    elif raw.startswith(b"\xfe\xff"):
        try:
            return raw.decode("utf-16-be").lstrip("\ufeff"), True
        except UnicodeDecodeError:
            pass
    else:
        encoding = _looks_like_utf16(raw)
        if encoding is not None:
            try:
                return raw.decode(encoding), True
            except UnicodeDecodeError:
                pass

    for encoding in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), False
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace"), False


def _decode(raw: bytes) -> str:
    """Decode bytes using the best available text encoding."""
    return _decode_with_encoding(raw)[0]


def _from_plain(path: Path, limit: int, max_bytes: int) -> str:
    try:
        with path.open("rb") as fh:
            raw = fh.read(min(max_bytes, limit * 4))
    except OSError:
        return ""
    text, was_utf16 = _decode_with_encoding(raw)
    # UTF-16 naturally contains NUL bytes in its encoded representation, so
    # detect it first.  A decoded NUL still indicates binary or malformed
    # content and is rejected just as it was for other text formats.
    if (not was_utf16 and b"\x00" in raw[:1024]) or (
        was_utf16 and "\x00" in text[:1024]
    ):
        return ""  # binary masquerading as text
    return _clean(text, limit)


# RTF groups that contain document machinery rather than prose.
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


class _BudgetReader:
    """Seekable file facade that enforces a cumulative read limit."""

    def __init__(self, source, max_bytes: int) -> None:
        self._source = source
        self._remaining = max(0, max_bytes)

    def read(self, size: int = -1) -> bytes:
        if self._remaining == 0:
            return b""
        allowed = self._remaining if size < 0 else min(size, self._remaining)
        data = self._source.read(allowed)
        self._remaining -= len(data)
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._source.seek(offset, whence)

    def tell(self) -> int:
        return self._source.tell()

    def seekable(self) -> bool:
        return True


def _from_pdf(path: Path, limit: int, max_bytes: int) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:  # noqa: BLE001
        return ""
    # Best-effort extraction should not leak dependency diagnostics for a
    # damaged third-party PDF into an otherwise Unix-friendly command.
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    try:
        # PDF cross-reference tables can point anywhere in the file.  Feeding
        # a parser a partial large document is both slow and usually fruitless;
        # fall back to filename evidence when the file exceeds the read budget.
        if path.stat().st_size > max_bytes:
            return ""
        with path.open("rb", buffering=0) as source:
            reader = PdfReader(_BudgetReader(source, max_bytes))
            chunks = []
            for page in reader.pages[:_MAX_PDF_PAGES]:
                chunks.append(page.extract_text() or "")
                if sum(len(c) for c in chunks) >= limit:
                    break
            return _clean(" ".join(chunks), limit)
    except Exception:  # noqa: BLE001
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
    """Return readable text, if any."""
    if entry.size == 0 or not is_textual(entry.kind):
        return ""

    ext, path = entry.ext, entry.path
    limit, max_bytes = settings.text_excerpt_chars, settings.max_read_bytes

    if ext in _ZIP_MEMBERS:
        return _from_zip_xml(path, ext, limit, max_bytes)
    if ext == "pdf":
        return _from_pdf(path, limit, max_bytes)
    if ext == "rtf":
        return _from_rtf(path, limit, max_bytes)
    if ext in {"html", "htm", "xhtml", "xml"}:
        return _from_html(path, limit, max_bytes)
    if ext in {"doc", "ppt", "xls"}:
        return _from_legacy_doc(path, limit, max_bytes)
    return _from_plain(path, limit, max_bytes)
