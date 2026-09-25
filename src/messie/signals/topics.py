"""Signals for unrelated content sharing a folder."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from messie.result import Finding
from messie.signals import ramp, signal
from messie.tokens import name_tokens

if TYPE_CHECKING:  # pragma: no cover
    from messie.analyze import SignalContext


# Diminishing contribution from each additional subject.
_TOPIC_DECAY = 0.45
_MIN_UNRELATED_SEPARATION = 0.10
_SHARED_NAME_THREAD = 0.35


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _dominant_subject(analysis: SignalContext) -> np.ndarray | None:
    """Return the vector for the largest meaningful cluster."""
    clustering = analysis.clustering
    meaningful = analysis.meaningful_clusters()
    if clustering is None or not meaningful:
        return None
    biggest = max(meaningful, key=lambda cid: len(clustering.groups[cid]))
    members = clustering.groups[biggest]
    if members.size == 0:
        return None
    return _unit(analysis.vectors[members].mean(axis=0))


def _unit(vector: np.ndarray) -> np.ndarray:
    """Return a unit-length copy of a profile, or a zero vector."""
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-8:
        return np.zeros_like(vector)
    return vector / norm


def _relative(folder: Path, analysis: SignalContext) -> str:
    """A subfolder named the way a person would say it: Archive/2023/Taxes."""
    try:
        return str(folder.resolve().relative_to(analysis.path.resolve()))
    except ValueError:
        return folder.name


def _unrelated_set(analysis: SignalContext, candidates: list[int]) -> list[int]:
    """Largest-first greedy pick of clusters that are unrelated to each other."""
    clustering = analysis.clustering
    assert clustering is not None
    sim = clustering.group_similarity
    ceiling = analysis.thresholds.unrelated

    chosen: list[int] = []

    def has_shared_name_thread(first: int, second: int) -> bool:
        left = {
            token
            for index in clustering.groups[first]
            for token in name_tokens(analysis.files[int(index)].stem)
        }
        right = {
            token
            for index in clustering.groups[second]
            for token in name_tokens(analysis.files[int(index)].stem)
        }
        if not left or not right:
            return False
        return len(left & right) / len(left | right) >= _SHARED_NAME_THREAD

    for cid in sorted(candidates, key=lambda cid: -len(clustering.groups[cid])):
        if all(
            sim[cid, other] < ceiling
            and not has_shared_name_thread(cid, other)
            for other in chosen
        ):
            chosen.append(cid)
    return chosen


@signal
def unrelated_topics(analysis: SignalContext) -> list[Finding]:
    clustering = analysis.clustering
    if clustering is None or len(clustering.groups) < 2:
        return []

    meaningful = analysis.meaningful_clusters()
    if len(meaningful) < 2:
        return []

    chosen = _unrelated_set(analysis, meaningful)
    if len(chosen) < 2:
        return []

    covered = sum(len(clustering.groups[cid]) for cid in chosen)
    coverage = covered / max(1, analysis.n_files)

    sim = clustering.group_similarity
    pairs = [sim[a, b] for i, a in enumerate(chosen) for b in chosen[i + 1 :]]
    separation = 1.0 - max(0.0, float(np.mean(pairs))) / max(
        1e-6, analysis.thresholds.unrelated
    )
    if separation < _MIN_UNRELATED_SEPARATION:
        return []
    sharpness = 0.8 + 0.2 * max(0.0, min(1.0, separation))

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


_NO_THREAD_SHARE = 0.65


def _judgeable(analysis: SignalContext) -> np.ndarray:
    """Return files with enough text for topical comparison."""
    floor = analysis.settings.min_text_chars
    return np.array(
        [
            bool(analysis.topical[i]) and len(analysis.texts[i]) >= floor
            for i in range(analysis.n_files)
        ],
        dtype=bool,
    )


def _loose_fraction(analysis: SignalContext) -> tuple[float, np.ndarray]:
    """Return the unattached share and judgeable file indices."""
    clustering = analysis.clustering
    eligible = np.flatnonzero(_judgeable(analysis)) if analysis.n_files else np.zeros(0, int)
    if clustering is None or eligible.size == 0:
        return 0.0, eligible
    meaningful = set(analysis.meaningful_clusters())
    grouped = sum(1 for i in eligible if int(clustering.labels[i]) in meaningful)
    return 1.0 - grouped / int(eligible.size), eligible


@signal
def unattached_files(analysis: SignalContext) -> list[Finding]:
    """Report files that do not belong to a meaningful group."""
    clustering = analysis.clustering
    if clustering is None or analysis.n_files < 2:
        return []

    loose, eligible = _loose_fraction(analysis)
    if eligible.size < max(4, analysis.settings.min_files_to_judge):
        return []

    severity = ramp(loose, 0.20, 0.95)
    if severity <= 0:
        return []

    meaningful = set(analysis.meaningful_clusters())
    loners = [int(i) for i in eligible if int(clustering.labels[i]) not in meaningful]
    if len(loners) < 3:
        return []
    loners.sort(key=lambda i: clustering.closest_similarity[i])

    subjects = len({int(clustering.labels[i]) for i in eligible if clustering.labels[i] >= 0})
    total_thread = loose >= _NO_THREAD_SHARE

    if total_thread:
        code = "no_common_thread"
        headline = "Nothing in this folder goes with anything else."
        detail = (
            f"{eligible.size} readable files and {subjects} different subjects "
            f"between them — there is no thread running through this folder."
        )
    else:
        code = "strays"
        headline = f"{len(loners)} files match nothing else here."
        detail = f"{loose:.0%} of the readable files in this folder stand alone."

    return [
        Finding(
            code=code,
            severity=severity,
            headline=headline,
            detail=detail,
            examples=analysis.names(loners, limit=4),
            data={
                "count": len(loners),
                "readable": int(eligible.size),
                "subjects": subjects,
                "loose_fraction": round(loose, 3),
                "files": [analysis.files[i].name for i in loners[:20]],
            },
        )
    ]


@signal
def misfiled_neighbours(analysis: SignalContext) -> list[Finding]:
    """Report loose files resembling a descendant folder."""
    if not analysis.child_profiles or analysis.n_files == 0:
        return []

    vectors = analysis.vectors
    if vectors.size == 0:
        return []

    margin = analysis.thresholds.misfiled_margin
    threshold = analysis.thresholds.cluster

    subdirs = list(analysis.child_profiles)
    profiles = np.stack([_unit(analysis.child_profiles[d]) for d in subdirs])
    if profiles.shape[1] != vectors.shape[1]:
        return []

    main = _dominant_subject(analysis)
    if main is not None:
        distinct = np.array([float(p @ main) < analysis.thresholds.unrelated for p in profiles])
        if not distinct.any():
            return []
        subdirs = [d for d, keep in zip(subdirs, distinct, strict=True) if keep]
        profiles = profiles[distinct]

    # Compare candidates with the dominant parent subject when one exists.
    # Other misplaced neighbours can form a small cluster of their own, so a
    # global leave-one-out mean would make each of them legitimize the others.
    # Fall back to leave-one-out when the parent has no meaningful subject.
    topical = np.flatnonzero(analysis.topical)
    if topical.size < 2:
        return []
    parent_sum = vectors[topical].sum(axis=0)
    scores = vectors @ profiles.T          # (n_files, n_subdirs)

    hits: dict[str, list[str]] = {}
    total = 0
    for i in range(vectors.shape[0]):
        if not analysis.topical[i] or not vectors[i].any():
            continue
        parent = main if main is not None else _unit(parent_sum - vectors[i])
        own = float(vectors[i] @ parent)
        best = int(np.argmax(scores[i]))
        child = float(scores[i, best])
        if own >= threshold:
            continue
        # A descendant profile is a summary of its files, so a coherent
        # subject can score below the cluster threshold when its vocabulary
        # is broad.  Once the parent attachment is demonstrably weak, permit
        # the margin-sized lower band; the two-file-per-descendant guard below
        # keeps this from turning an isolated weak match into a finding.
        child_floor = threshold - margin
        if child >= child_floor:
            hits.setdefault(_relative(subdirs[best], analysis), []).append(
                analysis.files[i].name
            )
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
                f"{'a folder' if len(hits) == 1 else 'folders'} further down."
            ),
            detail=f"{len(biggest[1])} of them resemble ./{biggest[0]}.",
            examples=biggest[1][:3],
            data={"by_subdir": {k: v[:20] for k, v in hits.items()}, "count": total},
        )
    ]
