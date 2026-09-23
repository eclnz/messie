"""Reading what a binary file says about itself.

messie understands documents by reading them. Archives, fonts and images it
could not read at all, so each was represented by the same stand-in phrase —
``photograph picture image`` for every photograph anybody has ever taken.

Byte-level similarity was tried first and measured. Normalized compression
distance separates files in the same real directory from files in different
ones with a gap of 0.72 for SVG (which is really text) and 0.13 for shared
libraries, but only 0.016 for PNG, 0.005 for TrueType and 0.002 for gzip.
Already-compressed formats are entropy-coded, so their bytes look random
whatever the content and NCD saturates near 1.0. It cannot see photographs, so
it is not used.

What works is container metadata, which is not a guess about a file but a
statement the file makes about itself. Read here and handed back as a short
phrase, it goes through the same embedding and clustering as any document's
text: no new signal, no new thresholds.

Scope is deliberately narrow, and set by what measurement supported:

    archives   the member list — a zip of holiday photos and a zip of tax
               papers are plainly different things, and the manifest says so
    fonts      family and foundry, worth 0.60 of separation between real font
               directories where there was none
    images     dimensions, which collapsed a real image folder from fifteen
               spurious clusters to three

EXIF and audio tags were built and then removed. Telling one camera's
photographs from another's is discrimination between things that are alike,
and a Pictures folder holding two cameras is normal rather than messy — so the
capability cost two dependencies and changed no verdict. Distinguishing very
similar things is not the job; flagging obviously mixed content is.
"""

from __future__ import annotations

import struct
import tarfile
import zipfile
from pathlib import Path

from messie.scan import FileEntry

#: Never read more than this from a file just to describe it.
_HEAD_BYTES = 4096
#: Archives can hold thousands of members; a sample says as much as all of them.
_MAX_MEMBERS = 60
#: Keep descriptions short. They say what a file is, not what it contains at
#: length, and they must stay below ``min_text_chars`` so that binaries are
#: never judged for failing to cohere.
_MAX_WORDS = 40

_ARCHIVE_EXTS = frozenset({"zip", "whl", "jar", "egg", "apk", "tar", "tgz"})
_FONT_EXTS = frozenset({"ttf", "otf", "ttc", "woff", "woff2"})
_TAR_SUFFIXES = (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz", ".tar.xz", ".txz")


def _clip(words: list[str]) -> str:
    seen: list[str] = []
    lowered: set[str] = set()
    for word in words:
        word = word.strip()
        if word and word.lower() not in lowered:
            seen.append(word)
            lowered.add(word.lower())
        if len(seen) >= _MAX_WORDS:
            break
    return " ".join(seen)


# --- archives ---------------------------------------------------------------


def _describe_archive(path: Path) -> str:
    """The member list. An archive is a folder that happens to be one file.

    A bare ``.gz`` or ``.bz2`` holds a single stream with no member list, and
    its original name is already in the filename, so nothing is attempted for
    those. That also stops ``tarfile.is_tarfile`` quietly decompressing a large
    file only to discover it is not a tar.
    """
    names: list[str] = []
    tar_like = path.name.lower().endswith(_TAR_SUFFIXES)
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()[:_MAX_MEMBERS]
        elif tar_like and tarfile.is_tarfile(path):
            with tarfile.open(path) as archive:
                names = archive.getnames()[:_MAX_MEMBERS]
    except Exception:  # noqa: BLE001 - a damaged archive simply says nothing
        return ""

    words: list[str] = []
    for name in names:
        stem = Path(name).stem
        words.extend(part for part in stem.replace("-", " ").replace("_", " ").split() if part)
    return _clip(words)


# --- fonts ------------------------------------------------------------------

#: The name-table entries worth reading: family, style, foundry.
_NAME_FAMILY, _NAME_SUBFAMILY, _NAME_VENDOR = 1, 2, 8
_WANTED_NAMES = (_NAME_FAMILY, _NAME_SUBFAMILY, _NAME_VENDOR)


def _describe_font(path: Path) -> str:
    """Family, style and foundry, straight out of the sfnt name table."""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) < 12:
        return ""

    try:
        base = struct.unpack(">I", data[12:16])[0] if data[:4] == b"ttcf" else 0
        count = struct.unpack(">H", data[base + 4 : base + 6])[0]
    except struct.error:
        return ""

    offset = length = 0
    for index in range(count):
        record = base + 12 + index * 16
        if record + 16 > len(data):
            return ""
        if data[record : record + 4] == b"name":
            offset, length = struct.unpack(">II", data[record + 8 : record + 16])
            break
    if not length or offset + 6 > len(data):
        return ""

    names, strings = struct.unpack(">HH", data[offset + 2 : offset + 6])
    found: dict[int, str] = {}
    for index in range(names):
        record = offset + 6 + index * 12
        if record + 12 > len(data):
            break
        platform, _enc, _lang, name_id, size, start = struct.unpack(
            ">HHHHHH", data[record : record + 12]
        )
        if name_id not in _WANTED_NAMES:
            continue
        raw = data[offset + strings + start : offset + strings + start + size]
        try:
            text = raw.decode("utf-16-be") if platform == 3 else raw.decode("latin-1")
        except (UnicodeDecodeError, LookupError):
            continue
        text = "".join(c for c in text if c.isprintable()).strip()
        if text:
            found.setdefault(name_id, text)

    parts = [found.get(name_id, "") for name_id in _WANTED_NAMES]
    return _clip(" ".join(part for part in parts if part).split())


# --- images -----------------------------------------------------------------


def _png_size(data: bytes) -> str:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return ""
    width, height = struct.unpack(">II", data[16:24])
    return f"{width}x{height}"


def _gif_size(data: bytes) -> str:
    if data[:3] != b"GIF" or len(data) < 10:
        return ""
    width, height = struct.unpack("<HH", data[6:10])
    return f"{width}x{height}"


def _jpeg_size(data: bytes) -> str:
    if data[:2] != b"\xff\xd8":
        return ""
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            height, width = struct.unpack(">HH", data[i + 5 : i + 9])
            return f"{width}x{height}"
        if marker in (0xD8, 0xD9):
            i += 2
            continue
        try:
            i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
        except struct.error:
            break
    return ""


def _describe_image(path: Path) -> str:
    """Dimensions, which is all an image honestly says without decoding it.

    Thin, but not nothing: it is what stopped a real folder of bullet graphics
    fragmenting into fifteen meaningless groups.
    """
    try:
        with path.open("rb") as handle:
            head = handle.read(_HEAD_BYTES)
    except OSError:
        return ""
    return _png_size(head) or _jpeg_size(head) or _gif_size(head)


# --- dispatch ---------------------------------------------------------------


def describe(entry: FileEntry) -> str:
    """What this binary says about itself, as a short phrase.

    Returns "" for anything with nothing to say, which the caller treats
    exactly as it treats a file with no readable text.
    """
    if entry.size == 0:
        return ""
    try:
        if entry.ext in _ARCHIVE_EXTS or entry.kind == "archive":
            return _describe_archive(entry.path)
        if entry.ext in _FONT_EXTS or entry.kind == "font":
            return _describe_font(entry.path)
        if entry.kind == "image":
            return _describe_image(entry.path)
    except Exception:  # noqa: BLE001 - describing a file must never fail a scan
        return ""
    return ""
