"""Materialising real files of many kinds.

Every builder writes a file with a genuine header and container structure for
its format, so messie's extension tables, kind detection and text extraction
all see something honest.

The text-bearing formats — .docx, .pptx, .xlsx, .odt, .epub, .pdf, .rtf,
.ipynb, .srt and the plain-text family — carry their content for real, because
extracting it is the thing under test.

Media and binary formats are structurally valid stubs, not real photographs or
recordings: correct magic bytes and containers, then deterministic filler.
messie never decodes them, so shape is all that is needed, and generating a
genuine JPEG would test the generator rather than the tool.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import struct
import tarfile
import textwrap
import zipfile
from pathlib import Path

# --- helpers ---------------------------------------------------------------


def _prepare(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _filler(seed: str, size: int) -> bytes:
    """Deterministic pseudo-random bytes, so a fixture is identical every run."""
    out = bytearray()
    block = seed.encode("utf-8")
    while len(out) < size:
        block = hashlib.blake2b(block, digest_size=64).digest()
        out += block
    return bytes(out[:size])


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in text.split("\n") if p.strip()]
    return parts or [text.strip() or "(empty)"]


# --- plain text family -----------------------------------------------------


def write_plain(path: Path, text: str) -> Path:
    _prepare(path).write_text(text, encoding="utf-8")
    return path


def write_srt(path: Path, text: str) -> Path:
    lines = []
    for i, chunk in enumerate(textwrap.wrap(text, 70)[:20], start=1):
        start, end = i * 3, i * 3 + 2
        lines.append(f"{i}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{chunk}\n")
    _prepare(path).write_text("\n".join(lines), encoding="utf-8")
    return path


def write_ipynb(path: Path, text: str) -> Path:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in _paragraphs(text)[:2]],
        },
        {
            "cell_type": "code",
            "execution_count": 1,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in _paragraphs(text)],
        },
    ]
    notebook = {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    _prepare(path).write_text(json.dumps(notebook, indent=1), encoding="utf-8")
    return path


def write_rtf(path: Path, text: str) -> Path:
    body = r" \par ".join(_paragraphs(text))
    body = body.replace("\\n", " ")
    content = r"{\rtf1\ansi\deff0 {\fonttbl{\f0 Helvetica;}}\fs22 " + body + "}"
    _prepare(path).write_text(content, encoding="ascii", errors="replace")
    return path


# --- OOXML / ODF / EPUB ----------------------------------------------------

_OOXML = "http://schemas.openxmlformats.org"
_ODF = "urn:oasis:names:tc:opendocument:xmlns"

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Types xmlns="{_OOXML}/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package'
    '.relationships+xml"/>'
    "</Types>"
)


def _rels(target: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{_OOXML}/package/2006/relationships">'
        f'<Relationship Id="rId1" Target="{target}" '
        f'Type="{_OOXML}/officeDocument/2006/relationships/officeDocument"/>'
        "</Relationships>"
    )


def write_docx(path: Path, text: str) -> Path:
    body = "".join(
        f"<w:p><w:r><w:t>{_xml_escape(p)}</w:t></w:r></w:p>" for p in _paragraphs(text)
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_OOXML}/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(_prepare(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _rels("word/document.xml"))
        zf.writestr("word/document.xml", document)
    return path


def write_pptx(path: Path, text: str) -> Path:
    chunks = _paragraphs(text)
    with zipfile.ZipFile(_prepare(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _rels("ppt/presentation.xml"))
        for index, chunk in enumerate(chunks, start=1):
            slide = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<p:sld xmlns:p="{_OOXML}/presentationml/2006/main" '
                f'xmlns:a="{_OOXML}/drawingml/2006/main"><p:cSld><p:spTree>'
                f"<p:sp><p:txBody><a:p><a:r><a:t>{_xml_escape(chunk)}</a:t></a:r></a:p>"
                "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
            )
            zf.writestr(f"ppt/slides/slide{index}.xml", slide)
    return path


def write_xlsx(path: Path, text: str) -> Path:
    items = "".join(f"<si><t>{_xml_escape(p)}</t></si>" for p in _paragraphs(text))
    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="{_OOXML}/spreadsheetml/2006/main">{items}</sst>'
    )
    with zipfile.ZipFile(_prepare(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _rels("xl/workbook.xml"))
        zf.writestr("xl/sharedStrings.xml", shared)
    return path


def write_odt(path: Path, text: str) -> Path:
    body = "".join(f"<text:p>{_xml_escape(p)}</text:p>" for p in _paragraphs(text))
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<office:document-content xmlns:office="{_ODF}:office:1.0" '
        f'xmlns:text="{_ODF}:text:1.0"><office:body><office:text>'
        f"{body}</office:text></office:body></office:document-content>"
    )
    with zipfile.ZipFile(_prepare(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        zf.writestr("content.xml", content)
    return path


def write_epub(path: Path, text: str) -> Path:
    body = "".join(f"<p>{_xml_escape(p)}</p>" for p in _paragraphs(text))
    chapter = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Chapter</title>'
        f"</head><body>{body}</body></html>"
    )
    with zipfile.ZipFile(_prepare(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("OEBPS/chapter1.xhtml", chapter)
    return path


# --- PDF -------------------------------------------------------------------


def _pdf_escape(line: str) -> str:
    return line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def write_pdf(path: Path, text: str) -> Path:
    """A real PDF whose text a PDF reader can extract."""
    drawn = ["BT", "/F1 11 Tf", "14 TL", "56 760 Td"]
    for paragraph in _paragraphs(text):
        for line in textwrap.wrap(paragraph, 88)[:40]:
            drawn.append(f"({_pdf_escape(line)}) Tj T*")
    drawn.append("ET")
    stream = "\n".join(drawn).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    size = len(objects) + 1
    out += f"xref\n0 {size}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()

    _prepare(path).write_bytes(bytes(out))
    return path


# --- media and binaries ----------------------------------------------------

_PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _iso_box(brand: bytes, compatible: bytes = b"mp41isom") -> bytes:
    payload = brand + struct.pack(">I", 512) + compatible
    return struct.pack(">I", len(payload) + 8) + b"ftyp" + payload


def write_image(path: Path, size: int = 24_000, seed: str = "img") -> Path:
    """JPEG, PNG, GIF, HEIC or a raw camera file, by extension."""
    ext = path.suffix.lower().lstrip(".")
    if ext == "png":
        head, tail = _PNG_1PX, b""
    elif ext in {"heic", "heif", "avif"}:
        head, tail = _iso_box(b"heic", b"mif1heic"), b""
    elif ext == "gif":
        head, tail = b"GIF89a" + struct.pack("<HH", 1, 1) + b"\x80\x00\x00", b"\x3b"
    else:  # jpeg family and raw formats all lead with the JFIF marker
        head = b"\xff\xd8\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00"
        head += b"\x00\x01\x00\x01\x00\x00"
        # A frame header, so the stub reports dimensions the way a real
        # photograph does rather than refusing to say how big it is.
        head += b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, 3024, 4032, 1)
        head += b"\x01\x11\x00"
        tail = b"\xff\xd9"
    body = _filler(seed + path.name, max(0, size - len(head) - len(tail)))
    _prepare(path).write_bytes(head + body + tail)
    return path


def write_audio(path: Path, size: int = 96_000, seed: str = "audio") -> Path:
    ext = path.suffix.lower().lstrip(".")
    if ext == "wav":
        body = _filler(seed + path.name, max(0, size - 44))
        head = (
            b"RIFF" + struct.pack("<I", len(body) + 36) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16)
            + b"data" + struct.pack("<I", len(body))
        )
    elif ext in {"m4a", "aac"}:
        head, body = _iso_box(b"M4A "), _filler(seed + path.name, size)
    else:  # mp3 and friends: an ID3v2 tag then frame data
        head = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00"
        body = _filler(seed + path.name, max(0, size - len(head)))
    _prepare(path).write_bytes(head + body)
    return path


def write_video(path: Path, size: int = 240_000, seed: str = "video") -> Path:
    head = _iso_box(b"isom")
    body = _filler(seed + path.name, max(0, size - len(head)))
    _prepare(path).write_bytes(head + body)
    return path


def write_font(path: Path, size: int = 40_000, seed: str = "font") -> Path:
    head = b"\x00\x01\x00\x00" + struct.pack(">HHHH", 4, 64, 4, 0)
    body = _filler(seed + path.name, max(0, size - len(head)))
    _prepare(path).write_bytes(head + body)
    return path


def write_installer(path: Path, size: int = 400_000, seed: str = "app") -> Path:
    """Windows .exe/.msi, macOS .dmg/.pkg, Linux .deb/.AppImage."""
    ext = path.suffix.lower().lstrip(".")
    if ext in {"exe", "msi"}:
        head = b"MZ" + _filler(seed, 58) + struct.pack("<I", 64) + b"PE\x00\x00"
        tail = b""
    elif ext == "pkg":
        head, tail = b"xar!" + struct.pack(">HIQ", 28, 1, 0), b""
    elif ext == "deb":
        head, tail = b"!<arch>\ndebian-binary   0           4         `\n2.0\n", b""
    elif ext == "appimage":
        head, tail = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8 + b"AI\x02", b""
    else:  # dmg carries its koly trailer at the end of the file
        head, tail = b"", b"koly" + struct.pack(">II", 4, 512)
    body = _filler(seed + path.name, max(0, size - len(head) - len(tail)))
    _prepare(path).write_bytes(head + body + tail)
    return path


def write_disk_image(path: Path, size: int = 600_000, seed: str = "iso") -> Path:
    out = bytearray(_filler(seed + path.name, size))
    out[:32768] = b"\x00" * 32768           # ISO 9660 system area
    out[32768:32769] = b"\x01"              # primary volume descriptor
    out[32769:32774] = b"CD001"
    _prepare(path).write_bytes(bytes(out))
    return path


def write_archive(path: Path, members: dict[str, str] | None = None) -> Path:
    """A real .zip or .tar.gz holding real members."""
    members = members or {"readme.txt": "Archived copy of the project files.\n"}
    name = path.name.lower()
    _prepare(path)
    if name.endswith((".tar.gz", ".tgz", ".tar")):
        mode = "w:gz" if name.endswith((".tar.gz", ".tgz")) else "w"
        with tarfile.open(path, mode) as tf:
            for member, body in members.items():
                data = body.encode("utf-8")
                info = tarfile.TarInfo(member)
                info.size = len(data)
                import io

                tf.addfile(info, io.BytesIO(data))
    else:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for member, body in members.items():
                zf.writestr(member, body)
    return path


def write_database(path: Path, rows: list[tuple[str, str]] | None = None) -> Path:
    """A real SQLite file, header and all."""
    _prepare(path)
    path.unlink(missing_ok=True)
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("CREATE TABLE notes (title TEXT, body TEXT)")
        connection.executemany(
            "INSERT INTO notes VALUES (?, ?)",
            rows or [("first", "a stored note"), ("second", "another stored note")],
        )
        connection.commit()
    finally:
        connection.close()
    return path


def write_shortcut(path: Path, target: str = "https://example.invalid/page") -> Path:
    ext = path.suffix.lower().lstrip(".")
    if ext == "url":
        body = f"[InternetShortcut]\nURL={target}\n"
    elif ext == "webloc":
        body = (
            '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0">'
            f"<dict><key>URL</key><string>{target}</string></dict></plist>"
        )
    else:
        body = "[Desktop Entry]\nType=Link\nName=Saved link\nURL=" + target + "\n"
    _prepare(path).write_text(body, encoding="utf-8")
    return path


def write_empty(path: Path) -> Path:
    _prepare(path).write_bytes(b"")
    return path


# --- dispatch --------------------------------------------------------------

#: Extensions whose writer carries the supplied text into the file.
_TEXT_WRITERS = {
    "docx": write_docx, "pptx": write_pptx, "xlsx": write_xlsx,
    "odt": write_odt, "ods": write_odt, "odp": write_odt,
    "epub": write_epub, "pdf": write_pdf, "rtf": write_rtf,
    "ipynb": write_ipynb, "srt": write_srt, "vtt": write_srt,
}

_BINARY_WRITERS = {
    "jpg": write_image, "jpeg": write_image, "png": write_image, "gif": write_image,
    "heic": write_image, "tiff": write_image, "webp": write_image, "cr2": write_image,
    "nef": write_image, "dng": write_image, "bmp": write_image,
    "mp3": write_audio, "wav": write_audio, "m4a": write_audio, "flac": write_audio,
    "aac": write_audio, "ogg": write_audio,
    "mp4": write_video, "mov": write_video, "mkv": write_video, "avi": write_video,
    "webm": write_video,
    "ttf": write_font, "otf": write_font, "woff": write_font,
    "exe": write_installer, "msi": write_installer, "dmg": write_installer,
    "pkg": write_installer, "deb": write_installer, "appimage": write_installer,
    "iso": write_disk_image, "img": write_disk_image, "vmdk": write_disk_image,
    "zip": write_archive, "tar": write_archive, "tgz": write_archive,
    "db": write_database, "sqlite": write_database, "sqlite3": write_database,
    "url": write_shortcut, "webloc": write_shortcut, "lnk": write_shortcut,
    "psd": write_image, "ai": write_image, "sketch": write_archive,
}


def write_file(path: Path, text: str = "") -> Path:
    """Write ``path`` as whatever its extension says it is.

    Formats that can hold prose get ``text``; media and binaries get a valid
    header and deterministic filler, seeded from the filename so a fixture is
    byte-identical every run.
    """
    ext = path.suffix.lower().lstrip(".")
    if path.name.lower().endswith((".tar.gz", ".tar.bz2")):
        return write_archive(path)
    if ext in _TEXT_WRITERS:
        return _TEXT_WRITERS[ext](path, text)
    if ext in _BINARY_WRITERS:
        writer = _BINARY_WRITERS[ext]
        if writer in (write_archive, write_database, write_shortcut):
            return writer(path)
        return writer(path, seed=text[:32] or path.stem)
    return write_plain(path, text)
