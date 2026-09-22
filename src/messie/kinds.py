"""What kind of thing a file is, judged from its name.

Kinds group extensions into things a person would name ("a photo", "a
spreadsheet"). Domains group kinds more coarsely, so that a folder mixing a
spreadsheet with a slide deck reads as less odd than one mixing a spreadsheet
with a disk image.
"""

from __future__ import annotations

import re

KIND_BY_EXT: dict[str, str] = {}


def _register(kind: str, exts: str) -> None:
    for e in exts.split():
        KIND_BY_EXT[e] = kind


_register("image", "jpg jpeg png gif bmp tiff tif webp heic heif raw cr2 nef arw dng svg ico avif")
_register("video", "mp4 mov avi mkv wmv flv webm m4v mpg mpeg 3gp mts")
_register("audio", "mp3 wav flac aac ogg m4a wma aiff opus mid midi")
_register("document", "doc docx odt rtf pages wpd")
_register("spreadsheet", "xls xlsx ods numbers")
_register("presentation", "ppt pptx odp key")
_register("pdf", "pdf")
_register("ebook", "epub mobi azw azw3 djvu fb2")
_register("text", "txt md markdown rst log tex org adoc")
_register("code", "py js ts jsx tsx java c h cpp hpp cs go rs rb php swift kt scala sh bash zsh "
                  "ps1 bat pl lua r m sql vim el hs ml clj ex exs dart sc")
_register("config", "json yaml yml toml ini cfg conf env properties plist xml editorconfig lock")
_register("data", "csv tsv parquet feather arrow jsonl ndjson xml sav dta rdata rds "
                  "npy npz mat h5 hdf5")
_register("notebook", "ipynb rmd qmd")
_register("archive", "zip tar gz bz2 xz 7z rar tgz tbz zst lz4 cab")
_register("installer", "exe msi dmg pkg deb rpm appimage apk snap flatpak")
_register("disk_image", "iso img vhd vmdk vdi qcow2 sparseimage")
_register("font", "ttf otf woff woff2 eot")
_register("database", "db sqlite sqlite3 mdb accdb realm")
_register("design", "psd ai xd fig sketch indd afdesign afphoto blend obj fbx stl step dwg dxf")
_register("subtitle", "srt vtt ass sub")
_register("shortcut", "lnk url webloc desktop alias")
_register("junk", "tmp temp part crdownload partial download bak old swp swo ds_store thumbs "
                  "lock pid err stackdump dmp")

DOMAIN_BY_KIND: dict[str, str] = {
    "image": "media", "video": "media", "audio": "media", "design": "media",
    "subtitle": "media", "font": "media",
    "document": "office", "spreadsheet": "office", "presentation": "office",
    "pdf": "office", "ebook": "office", "text": "office",
    "code": "dev", "config": "dev", "notebook": "dev", "data": "dev",
    "database": "dev",
    "archive": "system", "installer": "system", "disk_image": "system",
    "shortcut": "system", "junk": "system", "unknown": "other",
}

# Kinds whose contents are worth reading for meaning.
TEXTUAL_KINDS = frozenset(
    {"document", "presentation", "spreadsheet", "pdf", "ebook", "text", "code",
     "config", "notebook", "data", "subtitle"}
)

# --- clutter patterns ------------------------------------------------------

# Names that mean "this is a leftover", not "this is a file someone wanted".
DEBRIS_NAME_RE = re.compile(
    r"""^(
        ~\$.*              |   # Office lock files: ~$report.docx
        \._.*              |   # macOS resource forks
        \.DS_Store         |
        Thumbs\.db         |
        desktop\.ini       |
        Icon\r?            |
        .*\.(tmp|temp|part|partial|crdownload|swp|swo|bak|old|orig|rej)
    )$""",
    re.VERBOSE | re.IGNORECASE,
)

# "Untitled 3.docx", "New Text Document (2).txt", "document1.docx"
UNNAMED_RE = re.compile(
    r"^(untitled|unnamed|new\s+(text\s+)?(document|folder|file)|document|scan|image|"
    r"download|file)[\s_\-]*\(?\d*\)?$",
    re.IGNORECASE,
)

# Version-pileup markers, the sediment of "just one more revision".
VERSION_MARKER_RE = re.compile(
    r"(?:^|[\s_\-.])("
    r"final|final2|finalfinal|fin|draft|rev|revised|revision|version|ver|v\d+|"
    r"copy|copia|kopie|dup|duplicate|backup|bak|old|new|latest|current|"
    r"use\s*this|real|actual|updated|edit|edited|fix|fixed|\d{1,2}"
    r")(?:$|[\s_\-.])|\(\d+\)$|\s-\s*copy",
    re.IGNORECASE,
)

# Camera/phone/screenshot names carry no topical meaning at all.
OPAQUE_NAME_RE = re.compile(
    r"^(img|dsc|dscn|pxl|mvimg|vid|mov|photo|pic|image|screen\s?shot|screenshot|"
    r"capture|snap|scan|untitled|document|received|whatsapp|signal|fb|unnamed)"
    r"[\s_\-]*[\d\-_.\s]*$",
    re.IGNORECASE,
)


def kind_for(ext: str, name: str = "") -> str:
    """Kind for an extension (given without the dot, any case)."""
    if name and DEBRIS_NAME_RE.match(name):
        return "junk"
    return KIND_BY_EXT.get(ext.lower().lstrip("."), "unknown")


def domain_for(kind: str) -> str:
    return DOMAIN_BY_KIND.get(kind, "other")


def is_textual(kind: str) -> bool:
    return kind in TEXTUAL_KINDS


#: A phrase standing in for the kind itself. Files that carry no readable text
#: and no meaningful filename (IMG_4412.HEIC) still need *some* vector, and the
#: honest one is "this is a photo" — which groups them with the other photos
#: instead of making each one look like an unrelated stray.
KIND_PHRASE: dict[str, str] = {
    "image": "photograph picture image snapshot",
    "video": "video footage movie clip recording",
    "audio": "audio sound recording music track",
    "document": "written document text letter report",
    "spreadsheet": "spreadsheet table of numbers accounts",
    "presentation": "slide deck presentation talk",
    "pdf": "pdf document printed page",
    "ebook": "book ebook reading",
    "text": "plain text notes writing",
    "code": "source code program software",
    "config": "configuration settings file",
    "data": "dataset records data table",
    "notebook": "computational notebook analysis",
    "archive": "compressed archive bundle zip",
    "installer": "software installer package setup",
    "disk_image": "disk image system volume",
    "font": "typeface font",
    "database": "database file records",
    "design": "design artwork graphics project",
    "subtitle": "subtitles captions",
    "shortcut": "shortcut link",
    "junk": "temporary leftover file",
    "unknown": "file",
}


def kind_phrase(kind: str) -> str:
    return KIND_PHRASE.get(kind, "file")
