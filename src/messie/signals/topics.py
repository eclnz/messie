"""Signals about meaning: unrelated things sharing a folder.

This is the heart of messie. A folder of forty Word documents looks perfectly
uniform by file type; if half of them are tax paperwork and half are chapters
of a novel, it is a mess, and only the content says so.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from messie.signals import Finding, ramp, signal

if TYPE_CHECKING:  # pragma: no cover
    from messie.analyze import DirAnalysis


#: Each additional unrelated subject adds less than the one before it.
#: Two subjects -> 0.55, three -> 0.80, four -> 0.91.
_TOPIC_DECAY = 0.45


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _unrelated_set(analysis: DirAnalysis, candidates: list[int]) -> list[int]:
    """Largest-first greedy pick of clusters that are unrelated to each other."""
    clustering = analysis.clustering
    assert clustering is not None
    sim = clustering.link()
    ceiling = analysis.thresholds.unrelated
    sizes = clustering.sizes()

    chosen: list[int] = []
    for cid in sorted(candidates, key=lambda c: -sizes.get(c, 0)):
        if all(sim[cid, other] < ceiling for other in chosen):
            chosen.append(cid)
    return chosen


@signal
def unrelated_topics(analysis: DirAnalysis) -> list[Finding]:
    clustering = analysis.clustering
    if clustering is None or clustering.n_clusters < 2:
        return []

    meaningful = analysis.meaningful_clusters()
    if len(meaningful) < 2:
        return []

    chosen = _unrelated_set(analysis, meaningful)
    if len(chosen) < 2:
        return []

    sizes = clustering.sizes()
    covered = sum(sizes[cid] for cid in chosen)
    coverage = covered / max(1, analysis.n_files)

    # How far apart they actually are: centroids near zero similarity are
    # stronger evidence than ones just under the threshold.
    sim = clustering.link()
    pairs = [sim[a, b] for i, a in enumerate(chosen) for b in chosen[i + 1 :]]
    separation = 1.0 - max(0.0, float(np.mean(pairs))) / max(
        1e-6, analysis.thresholds.unrelated
    )
    sharpness = 0.8 + 0.2 * max(0.0, min(1.0, separation))

    # Two genuinely unrelated bodies of work in one folder is already a mess —
    # the canonical "my novel and my tax returns are in the same place" — so the
    # curve starts high and saturates rather than ramping up from nothing.
    crowding = 1.0 - _TOPIC_DECAY ** (len(chosen) - 1)
    severity = crowding * (0.5 + 0.5 * coverage) * sharpness

    groups = []
    for cid in chosen:
        members = analysis.members(cid)
        first, last = analysis.mtime_span(members)
        groups.append(
            {
                "label": analysis.label_of(cid),
                "count": len(members),
                "examples": analysis.names(members),
                "first_seen": first,
                "last_seen": last,
                "kinds": sorted({analysis.files[i].kind for i in members}),
            }
        )
    groups.sort(key=lambda g: -g["count"])

    return [
        Finding(
            code="unrelated_topics",
            severity=severity,
            headline=(
                f"{_plural(len(chosen), 'unrelated thing')} "
                f"{'is' if len(chosen) == 1 else 'are'} living in this folder."
            ),
            detail=f"{covered} of {analysis.n_files} files belong to one of them.",
            examples=[f"{g['label']} ({g['count']})" for g in groups],
            data={"groups": groups, "coverage": round(coverage, 3)},
        )
    ]


def _loose_fraction(analysis: DirAnalysis) -> tuple[float, np.ndarray]:
    """Share of readable files belonging to no group worth the name.

    Returns the fraction and the indices of the files we could actually read.
    """
    clustering = analysis.clustering
    eligible = np.flatnonzero(analysis.topical)
    if clustering is None or eligible.size == 0:
        return 0.0, eligible
    meaningful = set(analysis.meaningful_clusters())
    grouped = sum(1 for i in eligible if int(clustering.labels[i]) in meaningful)
    return 1.0 - grouped / int(eligible.size), eligible


@signal
def no_common_thread(analysis: DirAnalysis) -> list[Finding]:
    """A folder with no organising subject at all.

    This is the case the clustering signal cannot see. ``unrelated_topics``
    needs groups to compare, and a folder where every single file is about
    something different has none — so at the point the mess is total, the
    flagship signal goes quiet. Saying so has to be done by counting the
    absence of structure rather than by finding it.
    """
    clustering = analysis.clustering
    if clustering is None:
        return []

    loose, eligible = _loose_fraction(analysis)
    if eligible.size < analysis.settings.min_files_to_judge:
        return []

    severity = ramp(loose, 0.5, 0.95)
    if severity <= 0:
        return []

    subjects = len({int(clustering.labels[i]) for i in eligible if clustering.labels[i] >= 0})
    loners = [int(i) for i in eligible if int(clustering.labels[i]) not in
              set(analysis.meaningful_clusters())]

    return [
        Finding(
            code="no_common_thread",
            severity=severity,
            headline="Nothing in this folder goes with anything else.",
            detail=(
                f"{eligible.size} readable files and {subjects} different subjects "
                f"between them — there is no thread running through this folder."
            ),
            examples=analysis.names(loners, limit=4),
            data={
                "readable": int(eligible.size),
                "subjects": subjects,
                "loose_fraction": round(loose, 3),
            },
        )
    ]


@signal
def strays(analysis: DirAnalysis) -> list[Finding]:
    """Files that match nothing else here.

    Only files we could actually read are eligible: a photo we cannot open is
    uninformative, not unrelated, and holding that against the folder would
    flag every photo album ever made.
    """
    clustering = analysis.clustering
    if clustering is None or analysis.n_files < 2:
        return []

    loose, eligible = _loose_fraction(analysis)
    if eligible.size < 4:
        return []
    if loose >= 0.5:
        # Nearly everything here stands alone, which is not "a few files do not
        # belong" but "there is nothing to belong to". no_common_thread says
        # that better, and counting it twice would inflate the score.
        return []

    floor = analysis.thresholds.stray
    loners = [int(i) for i in eligible if clustering.best_other[i] < floor]
    if len(loners) < 3:
        return []

    fraction = len(loners) / int(eligible.size)
    severity = ramp(fraction, 0.15, 0.55)
    if severity <= 0:
        return []

    loners.sort(key=lambda i: clustering.best_other[i])
    return [
        Finding(
            code="strays",
            severity=severity,
            headline=f"{len(loners)} files match nothing else here.",
            detail=f"{fraction:.0%} of the readable files in this folder stand alone.",
            examples=analysis.names(loners, limit=4),
            data={
                "count": len(loners),
                "fraction": round(fraction, 3),
                "files": [analysis.files[i].name for i in loners[:20]],
            },
        )
    ]


@signal
def misfiled_neighbours(analysis: DirAnalysis) -> list[Finding]:
    """Loose files that read like the contents of a subfolder sitting right there.

    Reported as an observation. Where they ought to go is not messie's call.
    """
    if not analysis.child_profiles or analysis.n_files == 0:
        return []

    vectors = analysis.vectors
    if vectors.size == 0:
        return []

    own_mean = vectors.mean(axis=0)
    margin = analysis.thresholds.misfiled_margin
    threshold = analysis.thresholds.cluster

    subdirs = list(analysis.child_profiles)
    profiles = np.stack([analysis.child_profiles[d] for d in subdirs])
    if profiles.shape[1] != vectors.shape[1]:
        return []

    scores = vectors @ profiles.T          # (n_files, n_subdirs)
    own = vectors @ own_mean               # (n_files,)

    hits: dict[str, list[str]] = {}
    total = 0
    for i in range(vectors.shape[0]):
        if not analysis.topical[i]:
            continue
        best = int(np.argmax(scores[i]))
        if scores[i, best] >= threshold and scores[i, best] > own[i] + margin:
            hits.setdefault(subdirs[best].name, []).append(analysis.files[i].name)
            total += 1

    hits = {k: v for k, v in hits.items() if len(v) >= 2}
    total = sum(len(v) for v in hits.values())
    if total < 2:
        return []

    severity = ramp(total / max(1, analysis.n_files), 0.04, 0.35)
    if severity <= 0:
        return []

    biggest = max(hits.items(), key=lambda kv: len(kv[1]))
    return [
        Finding(
            code="misfiled_neighbours",
            severity=severity,
            headline=(
                f"{total} loose files read like the contents of "
                f"{'a subfolder' if len(hits) == 1 else 'subfolders'} right here."
            ),
            detail=f"{len(biggest[1])} of them resemble ./{biggest[0]}.",
            examples=biggest[1][:3],
            data={"by_subdir": {k: v[:20] for k, v in hits.items()}, "count": total},
        )
    ]
