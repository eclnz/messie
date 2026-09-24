"""Tokenise filenames and extracted text."""

from __future__ import annotations

import re

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z]{2,})")

_SPLIT_RE = re.compile(r"[\W_]+", re.UNICODE)
_DIGITS_RE = re.compile(r"^\d+$")
_HEXISH_RE = re.compile(r"^[0-9a-f]{8,}$", re.IGNORECASE)
_VERSIONED_RE = re.compile(r"([^\W\d_]+?)v?(\d+)", re.UNICODE)
_VNUM_RE = re.compile(r"v\d+")

REVISION_WORDS: frozenset[str] = frozenset(
    {
        "final", "finalfinal", "draft", "copy", "copia", "kopie", "backup", "bak",
        "old", "new", "latest", "current", "version", "ver", "rev", "revised",
        "revision", "updated", "update", "edited", "fixed", "temp", "tmp",
        "duplicate", "dup", "real", "actual", "use", "please",
    }
)

GENERIC_WORDS: frozenset[str] = frozenset(
    {
        "untitled", "unnamed", "document", "doc", "file", "scan", "scanned",
        "img", "image", "pic", "picture", "photo", "screenshot", "screen", "shot",
        "capture", "dsc", "dscn", "pxl", "mvimg", "vid", "download", "downloaded",
        "received", "export", "exported", "output", "test", "misc", "stuff",
        "things", "various", "other", "asset", "item", "edit", "fix", "the", "and",
        "for", "with", "from", "this", "that", "pdf", "docx",
        "at", "in", "on", "of", "to", "by", "is", "it", "as", "an", "or", "my",
        "a", "we", "us", "be", "do", "no", "so", "up",
    }
)

NOISE_WORDS: frozenset[str] = REVISION_WORDS | GENERIC_WORDS

_MONTHS = frozenset(
    {
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "sept",
        "oct", "nov", "dec", "january", "february", "march", "april", "june",
        "july", "august", "september", "october", "november", "december",
    }
)


def split_words(raw: str) -> list[str]:
    """Break an identifier-ish string into lowercase words."""
    spaced = _CAMEL_RE.sub(" ", raw)
    return [w.lower() for w in _SPLIT_RE.split(spaced) if w]


def _unversion(word: str) -> str:
    """Strip a version suffix from a revision word."""
    match = _VERSIONED_RE.fullmatch(word)
    if match and match.group(1) in REVISION_WORDS:
        return match.group(1)
    return word


def name_tokens(stem: str, *, drop_noise: bool = True) -> list[str]:
    """Meaningful words from a filename stem."""
    out = []
    for raw in split_words(stem):
        word = _unversion(raw)
        if len(word) < 2 or _DIGITS_RE.match(word) or _HEXISH_RE.match(word):
            continue
        if word in _MONTHS:
            continue
        if drop_noise and word in NOISE_WORDS:
            continue
        if _VNUM_RE.fullmatch(word):
            continue
        out.append(word)
    return out


def name_phrase(stem: str) -> str:
    """A filename rendered as the phrase a person would read out of it."""
    return " ".join(name_tokens(stem))


def content_tokens(text: str, limit: int = 400) -> list[str]:
    """Words from extracted text, for keyword labelling."""
    out = []
    for word in split_words(text):
        if len(word) < 3 or _DIGITS_RE.match(word) or word in NOISE_WORDS:
            continue
        out.append(word)
        if len(out) >= limit:
            break
    return out


def version_markers(stem: str) -> list[str]:
    """Revision markers present in a filename."""
    words = split_words(stem)
    markers = [w for w in words if _unversion(w) in REVISION_WORDS]
    if any(_VNUM_RE.fullmatch(w) for w in words) or re.search(r"\(\s*\d+\s*\)\s*$", stem):
        markers.append("version-suffix")
    return markers


def base_stem(stem: str) -> str:
    """Remove version noise from a filename stem."""
    kept = [
        w
        for w in (_unversion(raw) for raw in split_words(stem))
        if w not in NOISE_WORDS and not _DIGITS_RE.match(w) and not _VNUM_RE.fullmatch(w)
    ]
    return " ".join(kept)
