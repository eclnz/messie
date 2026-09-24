"""Signals about time: folders that accreted rather than got filled."""

from __future__ import annotations

import time
from collections import Counter
from typing import TYPE_CHECKING

from messie.signals import Finding, ramp, signal

if TYPE_CHECKING:  # pragma: no cover
    from messie.result import SignalContext

_DAY = 86400.0


def _year(ts: float) -> str:
    return time.strftime("%Y", time.localtime(ts)) if ts else "?"


@signal
def time_strata(analysis: SignalContext) -> list[Finding]:
    """Distinct eras of stuff, on distinct subjects, in the same folder.

    Both conditions matter. A folder of holiday photos spanning ten years is a
    photo album, not a mess; it only becomes one when each era is also *about*
    something different — the signature of a place things get dropped rather
    than a place things are kept.
    """
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

    # What is each era mostly about?
    dominant: list[int] = []
    for era in eras:
        labels = Counter(int(clustering.labels[i]) for i in era if clustering.labels[i] >= 0)
        dominant.append(labels.most_common(1)[0][0] if labels else -1)

    distinct = len({d for d in dominant if d >= 0})
    if distinct < 2:
        return []  # same subject over a long time: an archive, not a mess

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
