"""Turning filenames and text into words.

Filenames are dense with meaning but hostile to tokenisers:
``2023_Tax-Return_FINALv2 (copy).docx`` has to become
``tax return`` with the noise stripped, so that it embeds like the phrase a
person would use for it.
"""

from __future__ import annotations

import re

# Split lower->upper ("taxReturn"), and the tail of an acronym run, but only
# where a real lowercase word follows: "XMLParser" splits, "FINALv2" must not
# become "FINA"+"Lv2".
#
# This one stays ASCII. Python's re has no \p{Lu}, so matching accented capitals
# would mean a third-party regex engine, and a capital in the middle of a word
# is rare enough that it is not worth the dependency. "Crème Brûlée" splits on
# its space like any other name; only "crèmeBrûlée" would be missed.
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z]{2,})")

# Split on anything that is not a letter or digit *in any script*. An ASCII
# class here would treat every accented letter as a separator and quietly
# shred the word around it: "Déclaration" became "claration", "réunion" became
# "union", "café" became "caf". Underscore is a word character to \w, so it has
# to be listed as a separator explicitly.
_SPLIT_RE = re.compile(r"[\W_]+", re.UNICODE)
_DIGITS_RE = re.compile(r"^\d+$")
_HEXISH_RE = re.compile(r"^[0-9a-f]{8,}$", re.IGNORECASE)
_VERSIONED_RE = re.compile(r"([^\W\d_]+?)v?(\d+)", re.UNICODE)
_VNUM_RE = re.compile(r"v\d+")

#: Words meaning "another go at the same thing". Their presence in a name is
#: what separates a pile of revisions from an ordinary numbered series, so
#: these are tracked separately from merely generic words.
REVISION_WORDS: frozenset[str] = frozenset(
    {
        "final", "finalfinal", "draft", "copy", "copia", "kopie", "backup", "bak",
        "old", "new", "latest", "current", "version", "ver", "rev", "revised",
        "revision", "updated", "update", "edited", "fixed", "temp", "tmp",
        "duplicate", "dup", "real", "actual", "use", "please",
    }
)

#: Words that say nothing about what a file is about. Generic on their own —
#: "document" in a filename is not evidence of anything.
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

#: Everything stripped from topic signals.
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
    """Strip a trailing version number, but only where what remains is itself a
    revision word — so ``finalv2`` becomes ``final`` while ``w2`` is left alone."""
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
    """Revision words present in a name — the sediment of repeated saving.

    Only genuine revision words count. "tax_document_04" is a numbered series,
    not a pile of drafts, and must not be mistaken for one.
    """
    words = split_words(stem)
    markers = [w for w in words if _unversion(w) in REVISION_WORDS]
    # A bare "v3" or a trailing "(2)" is a version marker with no word to it.
    if any(_VNUM_RE.fullmatch(w) for w in words) or re.search(r"\(\s*\d+\s*\)\s*$", stem):
        markers.append("version-suffix")
    return markers


def base_stem(stem: str) -> str:
    """The stem with version noise removed, for grouping near-identical names.

    ``report.docx``, ``report_final.docx`` and ``report_v2 (copy).docx`` all
    reduce to ``report``, which is what makes them one pile.
    """
    kept = [
        w
        for w in (_unversion(raw) for raw in split_words(stem))
        if w not in NOISE_WORDS and not _DIGITS_RE.match(w) and not _VNUM_RE.fullmatch(w)
    ]
    return " ".join(kept)
