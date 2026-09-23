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
    images     dimensions always, and with Pillow installed the kind of image
               it is — photograph, scan, screenshot — from its EXIF

Audio tags were built and removed. Telling one album from another is
discrimination between things that are alike, and it changed no verdict.

EXIF was removed for the same reason and then brought back, because the reason
was wrong. The case first tested was one camera roll against another, which is
also things that are alike, and which a Pictures folder holds quite normally.
The case that matters is a folder mixing *kinds* of image, and there the
measurement is clear: given category words, seven of ten image-category pairs
fall below the threshold at which messie calls two groups unrelated — a scan
and a photograph sit at 0.138 against a line at 0.220. Photographs,
screenshots and memes stay above it and group together, which is the right
answer for three kinds of casual digital image.

Pillow is optional, so none of that costs anything to anyone who does not want
it; without it images still report their dimensions.
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


#: Words in an image's Software tag that say what produced it. The file is
#: naming its own producer, so this reads a stated fact rather than guessing
#: from pixels — but which words imply which category is a judgement, kept
#: deliberately short.
_SCREENSHOT_HINTS = ("shot", "snip", "capture", "grab", "screen")
_SCANNER_HINTS = ("scan", "epson", "canoscan", "twain", "xerox")


def _category_words(tags: dict) -> list[str]:
    """Name the kind of image, where the file says enough to name it.

    Dimensions alone do not separate categories: to an embedding, "4032x3024"
    and "1920x1080" are two terse number strings and nothing more. Words do.
    Measured against ideal category labels, seven of ten image-category pairs
    read as unrelated — a scan and a photograph at 0.138, a photograph and a
    diagram at 0.080, against an unrelated threshold of 0.220 — so a folder
    mixing them is reported as mixed. Photographs, screenshots and memes sit
    above that line and group together, which is the right answer for three
    kinds of casual digital image.
    """
    software = str(tags.get("Software", "")).strip()
    make = str(tags.get("Make", "")).strip()
    model = str(tags.get("Model", "")).strip()
    lowered = software.lower()

    if make or model:
        words = ["photograph", "taken", "with", "a", "camera", make, model]
        stamp = str(tags.get("DateTimeOriginal") or tags.get("DateTime") or "")
        if stamp[:4].isdigit():
            words.append(stamp[:4])
        return words
    if any(hint in lowered for hint in _SCANNER_HINTS):
        return ["scanned", "paper", "document", "from", "a", "scanner", software]
    if any(hint in lowered for hint in _SCREENSHOT_HINTS):
        return ["screenshot", "capture", "of", "a", "computer", "screen", software]
    if software:
        return ["image", "made", "with", software]
    return []


def _describe_image(path: Path) -> str:
    """What kind of image this is, and how big.

    Dimensions come from the file header and need nothing installed. They are
    thin — it is what stopped a real folder of bullet graphics fragmenting into
    fifteen meaningless groups — but they carry no sense of *category*.

    With Pillow present, EXIF adds that: a camera's make and model, a scanner's
    or screenshot tool's name. Those become words, and words are what the rest
    of messie can reason about. Without Pillow the dimensions still come back,
    so nothing breaks; there is simply less to say.
    """
    try:
        with path.open("rb") as handle:
            head = handle.read(_HEAD_BYTES)
    except OSError:
        return ""
    size = _png_size(head) or _jpeg_size(head) or _gif_size(head)

    try:
        from PIL import ExifTags, Image
    except Exception:  # noqa: BLE001 - optional; dimensions are still worth having
        return size

    try:
        with Image.open(path) as image:
            size = f"{image.width}x{image.height}"
            raw = image.getexif()
            tags = {ExifTags.TAGS.get(k, k): v for k, v in raw.items()} if raw else {}
    except Exception:  # noqa: BLE001 - unreadable image, header size still stands
        return size
    return _clip([*_category_words(tags), size])


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
