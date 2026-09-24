"""Classify files from their names."""

from __future__ import annotations

import re
from enum import Enum


class Kind(str, Enum):
    """A human-recognisable category of file."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    PDF = "pdf"
    EBOOK = "ebook"
    TEXT = "text"
    CODE = "code"
    CONFIG = "config"
    DATA = "data"
    NOTEBOOK = "notebook"
    ARCHIVE = "archive"
    INSTALLER = "installer"
    DISK_IMAGE = "disk_image"
    FONT = "font"
    DATABASE = "database"
    DESIGN = "design"
    SUBTITLE = "subtitle"
    SHORTCUT = "shortcut"
    JUNK = "junk"
    UNKNOWN = "unknown"


class Domain(str, Enum):
    """A broad group of related file kinds."""

    MEDIA = "media"
    OFFICE = "office"
    DEV = "dev"
    SYSTEM = "system"
    OTHER = "other"


EXTENSIONS_BY_KIND: dict[Kind, str] = {
    Kind.IMAGE: "jpg jpeg png gif bmp tiff tif webp heic heif raw cr2 nef arw dng svg ico avif",
    Kind.VIDEO: "mp4 mov avi mkv wmv flv webm m4v mpg mpeg 3gp mts",
    Kind.AUDIO: "mp3 wav flac aac ogg m4a wma aiff opus mid midi",
    Kind.DOCUMENT: "doc docx odt rtf pages wpd",
    Kind.SPREADSHEET: "xls xlsx ods numbers",
    Kind.PRESENTATION: "ppt pptx odp key",
    Kind.PDF: "pdf",
    Kind.EBOOK: "epub mobi azw azw3 djvu fb2",
    Kind.TEXT: "txt md markdown rst log tex org adoc",
    Kind.CODE: "py js ts jsx tsx java c h cpp hpp cs go rs rb php swift kt scala sh bash zsh "
    "ps1 bat pl lua r m sql vim el hs ml clj ex exs dart sc",
    Kind.CONFIG: "json yaml yml toml ini cfg conf env properties plist xml editorconfig lock",
    Kind.DATA: "csv tsv parquet feather arrow jsonl ndjson xml sav dta rdata rds "
    "npy npz mat h5 hdf5",
    Kind.NOTEBOOK: "ipynb rmd qmd",
    Kind.ARCHIVE: "zip tar gz bz2 xz 7z rar tgz tbz zst lz4 cab",
    Kind.INSTALLER: "exe msi dmg pkg deb rpm appimage apk snap flatpak",
    Kind.DISK_IMAGE: "iso img vhd vmdk vdi qcow2 sparseimage",
    Kind.FONT: "ttf otf woff woff2 eot",
    Kind.DATABASE: "db sqlite sqlite3 mdb accdb realm",
    Kind.DESIGN: "psd ai xd fig sketch indd afdesign afphoto blend obj fbx stl step dwg dxf",
    Kind.SUBTITLE: "srt vtt ass sub",
    Kind.SHORTCUT: "lnk url webloc desktop alias",
    Kind.JUNK: "tmp temp part crdownload partial download bak old swp swo ds_store thumbs "
    "lock pid err stackdump dmp",
}

KIND_BY_EXT: dict[str, Kind] = {
    extension: kind
    for kind, extensions in EXTENSIONS_BY_KIND.items()
    for extension in extensions.split()
}

DOMAIN_BY_KIND: dict[Kind, Domain] = {
    Kind.IMAGE: Domain.MEDIA,
    Kind.VIDEO: Domain.MEDIA,
    Kind.AUDIO: Domain.MEDIA,
    Kind.DESIGN: Domain.MEDIA,
    Kind.SUBTITLE: Domain.MEDIA, Kind.FONT: Domain.MEDIA,
    Kind.DOCUMENT: Domain.OFFICE, Kind.SPREADSHEET: Domain.OFFICE, Kind.PRESENTATION: Domain.OFFICE,
    Kind.PDF: Domain.OFFICE, Kind.EBOOK: Domain.OFFICE, Kind.TEXT: Domain.OFFICE,
    Kind.CODE: Domain.DEV,
    Kind.CONFIG: Domain.DEV,
    Kind.NOTEBOOK: Domain.DEV,
    Kind.DATA: Domain.DEV,
    Kind.DATABASE: Domain.DEV,
    Kind.ARCHIVE: Domain.SYSTEM, Kind.INSTALLER: Domain.SYSTEM, Kind.DISK_IMAGE: Domain.SYSTEM,
    Kind.SHORTCUT: Domain.SYSTEM, Kind.JUNK: Domain.SYSTEM, Kind.UNKNOWN: Domain.OTHER,
}

TEXTUAL_KINDS = frozenset(
    {Kind.DOCUMENT, Kind.PRESENTATION, Kind.SPREADSHEET, Kind.PDF, Kind.EBOOK, Kind.TEXT,
     Kind.CODE, Kind.CONFIG, Kind.NOTEBOOK, Kind.DATA, Kind.SUBTITLE}
)

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

UNNAMED_RE = re.compile(
    r"^(untitled|unnamed|new\s+(text\s+)?(document|folder|file)|document|scan|image|"
    r"download|file)[\s_\-]*\(?\d*\)?$",
    re.IGNORECASE,
)

VERSION_MARKER_RE = re.compile(
    r"(?:^|[\s_\-.])("
    r"final|final2|finalfinal|fin|draft|rev|revised|revision|version|ver|v\d+|"
    r"copy|copia|kopie|dup|duplicate|backup|bak|old|new|latest|current|"
    r"use\s*this|real|actual|updated|edit|edited|fix|fixed|\d{1,2}"
    r")(?:$|[\s_\-.])|\(\d+\)$|\s-\s*copy",
    re.IGNORECASE,
)

OPAQUE_NAME_RE = re.compile(
    r"^(img|dsc|dscn|pxl|mvimg|vid|mov|photo|pic|image|screen\s?shot|screenshot|"
    r"capture|snap|scan|untitled|document|received|whatsapp|signal|fb|unnamed)"
    r"[\s_\-]*[\d\-_.\s]*$",
    re.IGNORECASE,
)


def kind_for(ext: str, name: str = "") -> Kind:
    """Kind for an extension (given without the dot, any case)."""
    if name and DEBRIS_NAME_RE.match(name):
        return Kind.JUNK
    return KIND_BY_EXT.get(ext.lower().lstrip("."), Kind.UNKNOWN)


def domain_for(kind: Kind) -> Domain:
    return DOMAIN_BY_KIND[kind]


def is_textual(kind: Kind) -> bool:
    return kind in TEXTUAL_KINDS


KIND_PHRASE: dict[Kind, str] = {
    Kind.IMAGE: "photograph picture image snapshot",
    Kind.VIDEO: "video footage movie clip recording",
    Kind.AUDIO: "audio sound recording music track",
    Kind.DOCUMENT: "written document text letter report",
    Kind.SPREADSHEET: "spreadsheet table of numbers accounts",
    Kind.PRESENTATION: "slide deck presentation talk",
    Kind.PDF: "pdf document printed page",
    Kind.EBOOK: "book ebook reading",
    Kind.TEXT: "plain text notes writing",
    Kind.CODE: "source code program software",
    Kind.CONFIG: "configuration settings file",
    Kind.DATA: "dataset records data table",
    Kind.NOTEBOOK: "computational notebook analysis",
    Kind.ARCHIVE: "compressed archive bundle zip",
    Kind.INSTALLER: "software installer package setup",
    Kind.DISK_IMAGE: "disk image system volume",
    Kind.FONT: "typeface font",
    Kind.DATABASE: "database file records",
    Kind.DESIGN: "design artwork graphics project",
    Kind.SUBTITLE: "subtitles captions",
    Kind.SHORTCUT: "shortcut link",
    Kind.JUNK: "temporary leftover file",
    Kind.UNKNOWN: "file",
}


def kind_phrase(kind: Kind) -> str:
    return KIND_PHRASE[kind]
