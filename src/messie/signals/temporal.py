"""Signals about time: folders that accreted rather than got filled."""

from __future__ import annotations

import time
from collections import Counter
from typing import TYPE_CHECKING

import numpy as np

from messie.result import Finding
from messie.signals import ramp, signal

if TYPE_CHECKING:  # pragma: no cover
    from messie.analyze import SignalContext

_DAY = 86400.0


def _year(ts: float) -> str:
    return time.strftime("%Y", time.localtime(ts)) if ts else "?"


def _unit(vector: np.ndarray) -> np.ndarray:
    """Return a unit-length profile, preserving zero for empty evidence."""
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-8:
        return np.zeros_like(vector)
    return vector / norm


@signal
def time_strata(analysis: SignalContext) -> list[Finding]:
    """Report distinct topical eras in one folder."""
    clustering = analysis.clustering
    if clustering is None or analysis.n_files < analysis.settings.min_files_to_judge:
        return []

    ordered = sorted(range(analysis.n_files), key=lambda i: analysis.files[i].mtime)
    gap = analysis.settings.time_strata_gap_days * _DAY

    eras: list[list[int]] = [[ordered[0]]]
    for previous, current in zip(ordered, ordered[1:], strict=False):  # pairwise walk
        if analysis.files[current].mtime - analysis.files[previous].mtime > gap:
            eras.append([])
        eras[-1].append(current)

    eras = [era for era in eras if len(era) >= 3]
    if len(eras) < 2:
        return []

    dominant: list[int] = []
    for era in eras:
        labels = Counter(int(clustering.labels[i]) for i in era if clustering.labels[i] >= 0)
        dominant.append(labels.most_common(1)[0][0] if labels else -1)

    distinct = len({d for d in dominant if d >= 0})
    if distinct < 2:
        return []

    # Cluster ids describe how the files were partitioned, not whether two
    # eras are actually different subjects.  Compare each era's dominant
    # topical profile directly and require all pairs to be below the unrelated
    # threshold before calling the strata separate subjects.
    era_profiles: list[np.ndarray] = []
    for era, cid in zip(eras, dominant, strict=True):
        members = [i for i in era if int(clustering.labels[i]) == cid]
        if not members:
            members = [i for i in era if analysis.topical[i]]
        if not members:
            return []
        era_profiles.append(_unit(analysis.vectors[members].mean(axis=0)))

    profile_similarity = np.stack(era_profiles) @ np.stack(era_profiles).T
    pairs = profile_similarity[np.triu_indices(len(era_profiles), k=1)]
    if pairs.size == 0 or float(np.max(pairs)) >= analysis.thresholds.unrelated:
        return []

    severity = ramp(len(eras), 1, 4) * ramp(distinct, 1, 3) * 0.9
    if severity <= 0:
        return []

    spans = []
    for era, cid in zip(eras, dominant, strict=True):
        first, last = analysis.mtime_span(era)
        spans.append(
            {
                "from": _year(first),
                "to": _year(last),
                "count": len(era),
                "label": analysis.label_of(cid) if cid >= 0 else "unclear",
            }
        )

    return [
        Finding(
            code="time_strata",
            severity=severity,
            headline=(
                    f"This folder has {len(eras)} separate eras in it, "
                f"on {distinct} different subjects."
            ),
            detail=" · ".join(
                f"{s['from']}–{s['to']}: {s['count']} files ({s['label']})" for s in spans[:4]
            ),
            examples=[f"{s['from']}–{s['to']}" for s in spans[:4]],
            data={"eras": spans},
        )
    ]
