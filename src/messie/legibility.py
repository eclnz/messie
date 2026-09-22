"""Judging whether extracted text is actually language.

A folder does not only get messy by collecting unrelated things. It also
collects files that say nothing at all: downloads that finished corrupt, text
mangled by an encoding round-trip, base64 blobs saved with a .txt extension,
scans OCR'd into nonsense. Incoherence is itself evidence of neglect, and it
needs catching directly — a garbled file has no subject, so no amount of
clustering will ever notice it. Worse, feeding its vector into the clustering
lets noise masquerade as a topic.

The measure is deliberately cautious, because the ways of being legible are
many. Source code, CSV extracts, logs full of hashes and minified JavaScript
are all perfectly legitimate and none of them look like prose, so word-shape
tests are applied only to files that are supposed to be prose. Text in a script
this module cannot reason about — Chinese, Arabic, Hebrew, Devanagari — is
given the benefit of the doubt rather than being called gibberish for lacking
Latin vowels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_VOWELS = frozenset("aeiouyàáâäãåæèéêëìíîïòóôöõøùúûüýÿāēīōūąęįųœ")

#: Byte sequences that show up when UTF-8 is decoded as Latin-1 or cp1252.
_MOJIBAKE = ("Ã", "â€", "Â·", "Â ", "ï»¿", "â„¢", "Ð", "Ñ€", "ÐŸ", "å¤", "ã‚")

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_RUN_RE = re.compile(r"(.)\1{7,}", re.DOTALL)
_DELIMITERS = (",", "\t", ";", "|")
_KEY_VALUE_RE = re.compile(r"^\s*[\w.\-\[\]]+\s*[:=]\s*\S", re.MULTILINE)

#: Kinds whose files are meant to read as prose.
PROSE_KINDS = frozenset({"document", "pdf", "ebook", "presentation"})
#: Extensions under the catch-all "text" kind that are prose rather than data.
PROSE_EXTS = frozenset({"txt", "md", "markdown", "rst", "tex", "org", "adoc", ""})

#: Below this, a file is reported as garbled.
FLOOR = 0.45


@dataclass(frozen=True)
class Legibility:
    score: float
    reason: str = ""
    floor: float = FLOOR

    @property
    def garbled(self) -> bool:
        return self.score < self.floor


def is_prose(kind: str, ext: str) -> bool:
    """Whether word-shape tests are meaningful for this file."""
    if kind in PROSE_KINDS:
        return True
    return kind == "text" and ext.lower() in PROSE_EXTS


def looks_structured(sample: str) -> bool:
    """Whether this is a table or a settings list rather than prose.

    People save data with a .txt extension all the time — exported rows, a
    config dump, a list of readings. It has almost no letters in it and would
    fail every word-shape test, but there is nothing wrong with it, so it is
    exempted before those tests run rather than explained away afterwards.
    """
    lines = [line for line in sample.splitlines() if line.strip()][:40]
    if len(lines) < 3:
        return False

    for delimiter in _DELIMITERS:
        counts = [line.count(delimiter) for line in lines]
        present = [c for c in counts if c > 0]
        # The same delimiter, the same number of times, on most lines.
        if len(present) >= max(3, 0.7 * len(lines)) and len(set(present)) <= 2:
            return True

    return len(_KEY_VALUE_RE.findall("\n".join(lines))) >= 0.7 * len(lines)


def _ramp(value: float, low: float, high: float) -> float:
    if high <= low:
        return 1.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _band(value: float, low: float, high: float, slack: float) -> float:
    """1.0 inside [low, high], falling off over ``slack`` either side."""
    if low <= value <= high:
        return 1.0
    if value < low:
        return _ramp(value, low - slack, low)
    return 1.0 - _ramp(value, high, high + slack)


def legibility(text: str, *, prose: bool = True, floor: float = FLOOR) -> Legibility:
    """How much this text reads like language, from 0 to 1."""
    sample = text[:4000]
    if len(sample.strip()) < 60:
        # Too little to judge, and a short file is not evidence of anything.
        return Legibility(1.0, floor=floor)

    total = len(sample)
    scores: dict[str, float] = {}

    broken = sum(1 for c in sample if c == "�" or (ord(c) < 32 and c not in "\t\n\r"))
    scores["unreadable characters"] = 1.0 - min(1.0, (broken / total) * 25)

    printable = sum(1 for c in sample if c.isprintable() or c in "\t\n\r")
    scores["binary noise"] = _ramp(printable / total, 0.80, 0.98)

    mojibake = sum(sample.count(marker) for marker in _MOJIBAKE)
    scores["mangled encoding"] = 1.0 - min(1.0, (mojibake / total) * 120)

    longest_run = max((len(m.group(0)) for m in _RUN_RE.finditer(sample)), default=0)
    scores["repeated filler"] = 1.0 - _ramp(longest_run, 12, 60)

    if prose:
        letters = [c for c in sample if c.isalpha()]
        if not letters:
            scores["no words at all"] = 0.0
        else:
            latin = sum(1 for c in letters if ord(c) < 0x250)
            if latin / len(letters) >= 0.5 and not looks_structured(sample):
                scores.update(_word_shape(sample, letters))
            # Otherwise the text is in a script whose word shape this module
            # cannot judge, so it is left to the checks above.

    reason = min(scores, key=lambda key: scores[key])
    score = scores[reason]
    return Legibility(round(score, 3), reason if score < floor else "", floor)


def _word_shape(sample: str, letters: list[str]) -> dict[str, float]:
    tokens = _WORD_RE.findall(sample)
    if len(tokens) < 10:
        return {}

    with_vowel = sum(
        1 for t in tokens if len(t) <= 3 or any(c in _VOWELS for c in t.lower())
    )
    mean_length = sum(len(t) for t in tokens) / len(tokens)
    dense = len(letters) / max(1, len(sample) - sample.count(" "))

    # The longest stretch with no whitespace in it. Prose breaks every few
    # characters; a base64 payload saved as .txt runs for thousands. Measuring
    # whitespace density instead would flag a file that is one URL per line,
    # and counting only letter runs misses base64 entirely, since its digits
    # and slashes chop the letters into innocent-looking pieces.
    longest_chunk = max((len(chunk) for chunk in sample.split()), default=0)

    return {
        "not word-shaped": _ramp(with_vowel / len(tokens), 0.55, 0.85),
        "implausible word lengths": _band(mean_length, 3.0, 11.0, 1.2),
        "unbroken blobs of characters": 1.0 - _ramp(longest_chunk, 90, 400),
        "barely any letters": _ramp(dense, 0.30, 0.55),
    }


def assess(text: str, kind: str, ext: str, floor: float = FLOOR) -> Legibility:
    """Legibility of one file's extracted text, given what sort of file it is."""
    if not text.strip():
        return Legibility(1.0, floor=floor)
    return legibility(text, prose=is_prose(kind, ext), floor=floor)
