"""Group file vectors by subject."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

UNCLUSTERED = -1


@dataclass(frozen=True)
class Clustering:
    """The similarities and groups found in one folder."""

    labels: np.ndarray
    groups: tuple[np.ndarray, ...]
    file_similarity: np.ndarray
    group_similarity: np.ndarray
    closest_similarity: np.ndarray


def _readonly(values: np.ndarray) -> np.ndarray:
    values.setflags(write=False)
    return values


def _file_similarity(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return np.zeros((0, 0), dtype=np.float32)
    return np.clip(vectors @ vectors.T, -1.0, 1.0).astype(np.float32)


def _closest_similarity(similarity: np.ndarray) -> np.ndarray:
    if similarity.shape[0] < 2:
        return np.zeros(similarity.shape[0], dtype=np.float32)
    without_self = similarity.copy()
    np.fill_diagonal(without_self, -2.0)
    return without_self.max(axis=1).astype(np.float32)


def _leader_labels(
    vectors: np.ndarray, order: np.ndarray, threshold: float
) -> tuple[np.ndarray, list[np.ndarray], list[int]]:
    labels = np.full(vectors.shape[0], UNCLUSTERED, dtype=np.int32)
    sums: list[np.ndarray] = []
    counts: list[int] = []

    for index in order:
        vector = vectors[index]
        if not vector.any():
            continue
        if sums:
            means = np.stack(sums) / np.asarray(counts, dtype=np.float32)[:, None]
            scores = means @ vector
            closest = int(np.argmax(scores))
            if scores[closest] >= threshold:
                sums[closest] += vector
                counts[closest] += 1
                labels[index] = closest
                continue
        sums.append(vector.copy())
        counts.append(1)
        labels[index] = len(sums) - 1
    return labels, sums, counts


def _merge_mapping(sums: list[np.ndarray], counts: list[int], threshold: float) -> list[int]:
    """Return a seed-group id to final-group id mapping."""
    mapping = list(range(len(sums)))
    live_sums = [total.copy() for total in sums]
    live_counts = list(counts)
    remaining = set(range(len(sums)))

    while len(remaining) > 1:
        ids = sorted(remaining)
        totals = np.stack([live_sums[index] for index in ids])
        sizes = np.asarray([live_counts[index] for index in ids], dtype=np.float32)
        similarity = (totals @ totals.T) / np.outer(sizes, sizes)
        np.fill_diagonal(similarity, -2.0)

        first, second = divmod(int(np.argmax(similarity)), len(ids))
        if similarity[first, second] < threshold:
            break

        keep, drop = sorted((ids[first], ids[second]))
        live_sums[keep] += live_sums[drop]
        live_counts[keep] += live_counts[drop]
        remaining.remove(drop)
        for old, current in enumerate(mapping):
            if current == drop:
                mapping[old] = keep

    survivors = sorted(remaining, key=lambda index: (-live_counts[index], index))
    renumbered = {old: new for new, old in enumerate(survivors)}
    return [renumbered[current] for current in mapping]


def _final_labels(labels: np.ndarray, mapping: list[int]) -> np.ndarray:
    final = labels.copy()
    for old, new in enumerate(mapping):
        final[labels == old] = new
    return final


def _groups(labels: np.ndarray) -> tuple[np.ndarray, ...]:
    n_groups = int(labels.max()) + 1 if labels.size else 0
    return tuple(_readonly(np.flatnonzero(labels == group)) for group in range(n_groups))


def _group_similarity(vectors: np.ndarray, groups: tuple[np.ndarray, ...]) -> np.ndarray:
    if not groups:
        return np.zeros((0, 0), dtype=np.float32)
    sums = np.stack([vectors[group].sum(axis=0) for group in groups])
    sizes = np.asarray([len(group) for group in groups], dtype=np.float32)
    return ((sums @ sums.T) / np.outer(sizes, sizes)).astype(np.float32)


def _clustering(
    labels: np.ndarray,
    vectors: np.ndarray,
    file_similarity: np.ndarray,
    closest_similarity: np.ndarray,
) -> Clustering:
    groups = _groups(labels)
    return Clustering(
        labels=_readonly(labels),
        groups=groups,
        file_similarity=_readonly(file_similarity),
        group_similarity=_readonly(_group_similarity(vectors, groups)),
        closest_similarity=_readonly(closest_similarity),
    )


def cluster_vectors(vectors: np.ndarray, threshold: float) -> Clustering:
    """Cluster unit-length file vectors with deterministic average linkage."""
    similarity = _file_similarity(vectors)
    closest = _closest_similarity(similarity)
    labels = np.full(vectors.shape[0], UNCLUSTERED, dtype=np.int32)
    if vectors.shape[0] == 0:
        return _clustering(labels, vectors, similarity, closest)

    without_self = similarity.copy()
    np.fill_diagonal(without_self, -2.0)
    centrality = np.where(without_self > threshold, without_self, 0.0).sum(axis=1)
    order = np.argsort(-centrality, kind="stable")

    labels, sums, counts = _leader_labels(vectors, order, threshold)
    if sums:
        labels = _final_labels(labels, _merge_mapping(sums, counts, threshold))
    return _clustering(labels, vectors, similarity, closest)
