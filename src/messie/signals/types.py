"""Signals about the shape of a folder rather than its meaning."""

from __future__ import annotations

import math
from collections import Counter
from typing import TYPE_CHECKING

from messie.kinds import domain_for
from messie.signals import Finding, ramp, signal

if TYPE_CHECKING:  # pragma: no cover
    from messie.analyze import DirAnalysis

#: Reference spread for normalising entropy. Eight evenly-mixed kinds in one
#: folder is about as scrambled as folders get.
_REFERENCE_KINDS = 8


def _entropy(counts: list[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    return -sum((c / total) * math.log(c / total) for c in counts if c)


@signal
def type_soup(analysis: DirAnalysis) -> list[Finding]:
    """Many different sorts of thing, evenly mixed.

    Distinct from ``unrelated_topics``: this fires on a folder holding photos
    *and* installers *and* spreadsheets, regardless of what any of them are
    about.
    """
    if analysis.n_files < analysis.settings.min_files_to_judge:
        return []

    kinds = Counter(f.kind for f in analysis.files if f.kind != "junk")
    if len(kinds) < 3:
        return []

    normalised = _entropy(list(kinds.values())) / math.log(_REFERENCE_KINDS)
    floor = analysis.settings.type_soup_entropy_floor
    base = ramp(normalised, floor, 0.95)
    if base <= 0:
        return []

    domains = {domain_for(k) for k in kinds}
    # Three kinds from one domain (docs, slides, spreadsheets) is an office
    # folder. Three kinds from three domains is a drawer.
    severity = base * (0.55 + 0.45 * ramp(len(domains), 1, 3))

    top = kinds.most_common(5)
    return [
        Finding(
            code="type_soup",
            severity=severity,
            headline=f"{len(kinds)} different sorts of file are mixed together here.",
            detail=", ".join(f"{count} {kind}" for kind, count in top),
            examples=[kind for kind, _ in top],
            data={
                "kinds": dict(kinds),
                "domains": sorted(domains),
                "evenness": round(normalised, 3),
            },
        )
    ]


@signal
def overcrowded(analysis: DirAnalysis) -> list[Finding]:
    """Far too many things loose in one place."""
    soft = analysis.settings.overcrowded_soft_limit
    n = analysis.n_files + analysis.truncated
    if n <= soft:
        return []

    severity = ramp(n, soft, soft * 6)
    if severity <= 0:
        return []

    return [
        Finding(
            code="overcrowded",
            severity=severity,
            headline=f"{n} files sit loose in this one folder.",
            detail=f"Past about {soft}, a flat folder stops being browsable.",
            data={"count": n, "soft_limit": soft},
        )
    ]
