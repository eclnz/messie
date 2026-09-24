"""Bounded semantic descriptions for binary files."""

from __future__ import annotations

import struct
import tarfile
import zipfile
from collections.abc import Mapping
from pathlib import Path

from messie.config import DEFAULT_SETTINGS, Settings
from messie.kinds import Kind
from messie.scan import FileEntry

_HEAD_BYTES = 4096
_MAX_MEMBERS = 60
_MAX_WORDS = 40
_MAX_CHARS = 100
_ZIP_SUFFIXES = (".zip", ".whl", ".jar", ".egg", ".apk")
_TAR_SUFFIXES = (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz", ".tar.xz", ".txz")
_SFNT_EXTENSIONS = frozenset({"ttf", "otf"})
_NAME_FAMILY, _NAME_SUBFAMILY, _NAME_VENDOR = 1, 2, 8
_WANTED_NAME_IDS = (_NAME_FAMILY, _NAME_SUBFAMILY, _NAME_VENDOR)
_SCREENSHOT_HINTS = ("shot", "snip", "capture", "grab", "screen")
_SCANNER_HINTS = ("scan", "epson", "canoscan", "twain", "xerox")


def _phrase(parts: list[str]) -> str:
    """Return a short, de-duplicated phrase safe to send to an embedder."""
    kept: list[str] = []
    seen: set[str] = set()
    size = 0
    for part in parts:
        part = " ".join(part.split())
        key = part.casefold()
        if not part or key in seen or len(kept) == _MAX_WORDS:
            continue
        added = len(part) + bool(kept)
        if size + added > _MAX_CHARS:
            break
        kept.append(part)
        seen.add(key)
        size += added
    return " ".join(kept)


def _within_budget(path: Path, max_bytes: int) -> bool:
    try:
        return path.stat().st_size <= max_bytes
    except OSError:
        return False


def _read_limit(max_bytes: int) -> int:
    return max(0, max_bytes)


def _archive_parts(path: Path, max_bytes: int) -> list[str]:
    """Read a bounded archive member list, or nothing on failure."""
    if not _within_budget(path, max_bytes):
        return []
    try:
        if path.name.lower().endswith(_ZIP_SUFFIXES):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()[:_MAX_MEMBERS]
        else:
            with tarfile.open(path) as archive:
                names = archive.getnames()[:_MAX_MEMBERS]
    except (OSError, tarfile.TarError, zipfile.BadZipFile):
        return []

    return [
        part
        for name in names
        for part in Path(name).stem.replace("-", " ").replace("_", " ").split()
    ]


def _describe_archive(path: Path, max_bytes: int = DEFAULT_SETTINGS.max_read_bytes) -> str:
    return _phrase(_archive_parts(path, max_bytes))


def _describe_font(path: Path, max_bytes: int = DEFAULT_SETTINGS.max_read_bytes) -> str:
    """Read the sfnt name table without exceeding the byte budget."""
    try:
        with path.open("rb") as handle:
            data = handle.read(_read_limit(max_bytes))
    except OSError:
        return ""
    if len(data) < 12:
        return ""

    try:
        table_count = struct.unpack(">H", data[4:6])[0]
    except struct.error:
        return ""

    table_offset = table_length = 0
    for index in range(table_count):
        record = 12 + index * 16
        if record + 16 > len(data):
            break
        if data[record : record + 4] == b"name":
            table_offset, table_length = struct.unpack(">II", data[record + 8 : record + 16])
            break
    table_end = table_offset + table_length
    if not table_length or table_end > len(data) or table_offset + 6 > table_end:
        return ""

    name_count, string_offset = struct.unpack(">HH", data[table_offset + 2 : table_offset + 6])
    names: dict[int, str] = {}
    for index in range(name_count):
        record = table_offset + 6 + index * 12
        if record + 12 > table_end:
            break
        platform, _encoding, _language, name_id, size, start = struct.unpack(
            ">HHHHHH", data[record : record + 12]
        )
        if name_id not in _WANTED_NAME_IDS:
            continue
        value_start = table_offset + string_offset + start
        value_end = value_start + size
        if value_end > table_end:
            continue
        raw = data[value_start:value_end]
        try:
            value = raw.decode("utf-16-be") if platform == 3 else raw.decode("latin-1")
        except UnicodeDecodeError:
            continue
        value = "".join(char for char in value if char.isprintable())
        if value:
            names.setdefault(name_id, value)

    return _phrase([names.get(name_id, "") for name_id in _WANTED_NAME_IDS])


def _dims(width: int, height: int) -> str:
    return f"{width}x{height}" if width > 0 and height > 0 else ""


def _png_size(data: bytes) -> str:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return ""
    return _dims(*struct.unpack(">II", data[16:24]))


def _gif_size(data: bytes) -> str:
    if data[:3] != b"GIF" or len(data) < 10:
        return ""
    return _dims(*struct.unpack("<HH", data[6:10]))


def _jpeg_size(data: bytes) -> str:
    if data[:2] != b"\xff\xd8":
        return ""
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            height, width = struct.unpack(">HH", data[index + 5 : index + 9])
            return _dims(width, height)
        if marker in (0xD8, 0xD9):
            index += 2
            continue
        try:
            index += 2 + struct.unpack(">H", data[index + 2 : index + 4])[0]
        except struct.error:
            break
    return ""


def _image_size(data: bytes) -> str:
    return _png_size(data) or _jpeg_size(data) or _gif_size(data)


def _image_category(tags: Mapping[str, object]) -> list[str]:
    software = str(tags.get("Software", "")).strip()
    make = str(tags.get("Make", "")).strip()
    model = str(tags.get("Model", "")).strip()

    if make or model:
        parts = ["photograph", "camera", make, model]
        stamp = str(tags.get("DateTimeOriginal") or tags.get("DateTime") or "")
        return [*parts, stamp[:4]] if stamp[:4].isdigit() else parts
    if any(hint in software.lower() for hint in _SCANNER_HINTS):
        return ["scanned document", software]
    if any(hint in software.lower() for hint in _SCREENSHOT_HINTS):
        return ["screenshot", software]
    return ["image", software] if software else []


def _describe_image(path: Path, max_bytes: int = DEFAULT_SETTINGS.max_read_bytes) -> str:
    """Describe image dimensions and, when affordable, its EXIF category."""
    max_bytes = _read_limit(max_bytes)
    try:
        with path.open("rb") as handle:
            head = handle.read(min(_HEAD_BYTES, max_bytes))
    except OSError:
        return ""
    size = _image_size(head)
    if not _within_budget(path, max_bytes):
        return size

    try:
        from PIL import ExifTags, Image  # type: ignore
        with Image.open(path) as image:
            size = _dims(image.width, image.height)
            raw = image.getexif()
    except Exception:  # noqa: BLE001
        return size

    tags = {str(ExifTags.TAGS.get(key, key)): value for key, value in raw.items()} if raw else {}
    return _phrase([*_image_category(tags), size])


def _is_supported_archive(path: Path) -> bool:
    return path.name.lower().endswith(_ZIP_SUFFIXES + _TAR_SUFFIXES)


def describe_binary(
    entry: FileEntry, settings: Settings = DEFAULT_SETTINGS
) -> str:
    """Return bounded semantic fallback text for a non-text file."""
    if entry.size == 0:
        return ""
    try:
        if _is_supported_archive(entry.path):
            return _describe_archive(entry.path, settings.max_read_bytes)
        if entry.ext in _SFNT_EXTENSIONS:
            return _describe_font(entry.path, settings.max_read_bytes)
        if entry.kind is Kind.IMAGE:
            return _describe_image(entry.path, settings.max_read_bytes)
    except Exception:  # noqa: BLE001
        return ""
    return ""
