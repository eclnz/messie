"""Signals about leftovers: junk, revision pileups, and duplicates."""

from __future__ import annotations

import difflib
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from messie.kinds import DEBRIS_NAME_RE, UNNAMED_RE
from messie.signals import Finding, ramp, signal
from messie.tokens import base_stem, version_markers

if TYPE_CHECKING:  # pragma: no cover
    from messie.result import DirAnalysis

_HEAD_BYTES = 65536
_FULL_HASH_LIMIT = 64 << 20  # don't read a 4 GB video twice to prove it's a twin


@signal
def debris(analysis: DirAnalysis) -> list[Finding]:
    """Leftovers nobody chose to keep: lock files, partial downloads, empties."""
    found: list[tuple[str, str]] = []
    for entry in analysis.files:
        name = entry.name
        if DEBRIS_NAME_RE.match(name):
            found.append((name, "leftover"))
        elif entry.size == 0:
            found.append((name, "empty"))
        elif UNNAMED_RE.match(entry.stem):
            found.append((name, "never named"))

    if len(found) < 2:
        return []

    severity = max(
        ramp(len(found), 2, 12),
        ramp(len(found) / max(1, analysis.n_files), 0.05, 0.35),
    )
    reasons = sorted({reason for _, reason in found})
    return [
        Finding(
            code="debris",
            severity=severity,
            headline=f"{len(found)} files here are debris.",
            detail=", ".join(reasons),
            examples=[name for name, _ in found[:4]],
            data={"count": len(found), "files": [n for n, _ in found[:20]]},
        )
    ]


@signal
def version_pileups(analysis: DirAnalysis) -> list[Finding]:
    """Families of near-identical names: report, report_final, report_final_v2 (copy)."""
    families: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, entry in enumerate(analysis.files):
        stem = base_stem(entry.stem)
        if len(stem) < 3:
            continue
        families[(stem, entry.ext)].append(i)

    pileups = []
    for (stem, _ext), members in families.items():
        if len(members) < 3:
            continue
        marked = sum(1 for i in members if version_markers(analysis.files[i].stem))
        if marked == 0:
            continue  # a numbered series (page1, page2) is not a pileup
        pileups.append((stem, members))

    if not pileups:
        return []

    involved = sum(len(m) for _, m in pileups)
    severity = max(
        ramp(len(pileups), 1, 5),
        ramp(involved / max(1, analysis.n_files), 0.05, 0.4),
    ) * 0.9

    biggest = max(pileups, key=lambda p: len(p[1]))
    return [
        Finding(
            code="version_pileups",
            severity=severity,
            headline=(
                f"{len(pileups)} pile{'' if len(pileups) == 1 else 's'} of revisions "
                f"of the same thing ({involved} files)."
            ),
            detail=f"The deepest is '{biggest[0]}' at {len(biggest[1])} versions.",
            examples=analysis.names(biggest[1], limit=4),
            data={
                "families": {stem: analysis.names(m, limit=10) for stem, m in pileups[:10]},
                "count": involved,
            },
        )
    ]


def _digest(path: Path, size: int) -> str | None:
    try:
        with path.open("rb") as fh:
            head = fh.read(_HEAD_BYTES)
            if size <= _HEAD_BYTES:
                return hashlib.blake2b(head, digest_size=16).hexdigest()
            if size <= _FULL_HASH_LIMIT:
                hasher = hashlib.blake2b(digest_size=16)
                hasher.update(head)
                while chunk := fh.read(1 << 20):
                    hasher.update(chunk)
                return hasher.hexdigest()
            # Enormous file: head plus size is evidence enough.
            return hashlib.blake2b(head, digest_size=16).hexdigest() + f":{size}"
    except OSError:
        return None


@signal
def duplicates(analysis: DirAnalysis) -> list[Finding]:
    """The same content sitting here more than once, under any names."""
    by_size: dict[int, list[int]] = defaultdict(list)
    for i, entry in enumerate(analysis.files):
        if entry.size > 0:
            by_size[entry.size].append(i)

    groups: list[list[int]] = []
    for candidates in by_size.values():
        if len(candidates) < 2:
            continue
        by_hash: dict[str, list[int]] = defaultdict(list)
        for i in candidates:
            digest = _digest(analysis.files[i].path, analysis.files[i].size)
            if digest:
                by_hash[digest].append(i)
        groups.extend(members for members in by_hash.values() if len(members) > 1)

    exact_wasted = sum(len(g) - 1 for g in groups)

    near = _near_duplicates(analysis, {i for g in groups for i in g})
    total = exact_wasted + len(near)
    if total < 2:
        return []

    severity = ramp(total / max(1, analysis.n_files), 0.03, 0.3)
    if severity <= 0:
        return []

    examples: list[str] = []
    for group in sorted(groups, key=len, reverse=True)[:2]:
        examples.append(" = ".join(analysis.names(group, limit=3)))
    for a, b in near[:2]:
        examples.append(f"{analysis.files[a].name} ≈ {analysis.files[b].name}")

    parts = []
    if exact_wasted:
        parts.append(f"{exact_wasted} identical")
    if near:
        parts.append(f"{len(near)} near-identical")

    return [
        Finding(
            code="duplicates",
            severity=severity,
            headline=f"{total} files here are copies of something else here.",
            detail=" and ".join(parts) + ".",
            examples=examples[:4],
            data={
                "exact_groups": [analysis.names(g, limit=10) for g in groups[:10]],
                "near_pairs": [
                    [analysis.files[a].name, analysis.files[b].name] for a, b in near[:10]
                ],
            },
        )
    ]


#: Vector similarity only nominates a pair; the text has to agree, and the bar
#: is deliberately severe. Two invoices off the same template differ by a few
#: dozen characters in a few thousand and are emphatically not copies of each
#: other, so anything short of "the same document" must not be called one.
_TEXT_CONFIRM = 0.995
#: Below this much text, a one-word difference is a large share of the whole,
#: and the ratio stops meaning anything.
_MIN_TEXT_FOR_NEAR_DUP = 200
_COMPARE_CHARS = 2000


def _near_duplicates(analysis: DirAnalysis, already: set[int]) -> list[tuple[int, int]]:
    """Pairs that really are near-identical copies of each other.

    Vectors alone cannot carry this claim: static embeddings blur two documents
    that share a template into near-identical vectors even when they say quite
    different things. So the vectors nominate candidates and the extracted text
    has the final word.
    """
    clustering = analysis.clustering
    if clustering is None or clustering.sim.size == 0:
        return []

    threshold = analysis.thresholds.near_duplicate
    sim = np.triu(clustering.sim, k=1)
    pairs = np.argwhere(sim >= threshold)
    out: list[tuple[int, int]] = []
    seen: set[int] = set()
    for a, b in pairs:
        a, b = int(a), int(b)
        if a in already or b in already or b in seen:
            continue
        if not (analysis.topical[a] and analysis.topical[b]):
            continue
        text_a = analysis.texts[a][:_COMPARE_CHARS]
        text_b = analysis.texts[b][:_COMPARE_CHARS]
        if text_a and text_b:
            if min(len(text_a), len(text_b)) < _MIN_TEXT_FOR_NEAR_DUP:
                continue
            if difflib.SequenceMatcher(None, text_a, text_b).ratio() < _TEXT_CONFIRM:
                continue
        elif analysis.files[a].size != analysis.files[b].size:
            continue
        out.append((a, b))
        seen.add(b)
    return out
