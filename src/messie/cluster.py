"""Deterministic average-link clustering for file vectors."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

UNCLUSTERED = -1


@dataclass
class Clustering:
    labels: np.ndarray                # cluster id per file, or UNCLUSTERED
    sums: np.ndarray                  # (k, dim) sum of member vectors
    counts: np.ndarray                # (k,) members per cluster
    sim: np.ndarray                   # (n, n) pairwise cosine
    best_other: np.ndarray            # per file, similarity to its nearest neighbour
    _link: np.ndarray | None = field(default=None, repr=False)

    @property
    def n_clusters(self) -> int:
        return int(self.sums.shape[0])

    def members(self, cid: int) -> np.ndarray:
        return np.flatnonzero(self.labels == cid)

    def sizes(self) -> dict[int, int]:
        return {cid: int(self.counts[cid]) for cid in range(self.n_clusters)}

    def means(self) -> np.ndarray:
        """Mean member vector per cluster. Dotting a unit vector with one of
        these gives that file's average similarity to the cluster."""
        if self.n_clusters == 0:
            return self.sums
        return self.sums / self.counts[:, None]

    def link(self) -> np.ndarray:
        """(k, k) average-link similarity between clusters."""
        if self._link is None:
            if self.n_clusters == 0:
                self._link = np.zeros((0, 0), dtype=np.float32)
            else:
                outer = np.outer(self.counts, self.counts).astype(np.float32)
                self._link = (self.sums @ self.sums.T) / outer
        return self._link


def cosine_matrix(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return np.zeros((0, 0), dtype=np.float32)
    return np.clip(vectors @ vectors.T, -1.0, 1.0).astype(np.float32)


def _leader_pass(vectors: np.ndarray, order: np.ndarray, threshold: float):
    sums: list[np.ndarray] = []
    counts: list[int] = []
    labels = np.full(vectors.shape[0], UNCLUSTERED, dtype=np.int32)

    for idx in order:
        vector = vectors[idx]
        if not vector.any():
            continue  # nothing readable about this file; it joins nothing
        if sums:
            means = np.stack(sums) / np.asarray(counts, dtype=np.float32)[:, None]
            scores = means @ vector
            best = int(np.argmax(scores))
            if scores[best] >= threshold:
                sums[best] = sums[best] + vector
                counts[best] += 1
                labels[idx] = best
                continue
        sums.append(vector.copy())
        counts.append(1)
        labels[idx] = len(sums) - 1
    return labels, sums, counts


def _merge(sums: list[np.ndarray], counts: list[int], threshold: float) -> list[int]:
    """Exact average-link agglomeration. Returns old cluster id -> new id."""
    k = len(sums)
    mapping = list(range(k))
    live_sums = [s.copy() for s in sums]
    live_counts = list(counts)
    alive = set(range(k))

    while len(alive) > 1:
        ids = sorted(alive)
        matrix = np.stack([live_sums[i] for i in ids])
        sizes = np.asarray([live_counts[i] for i in ids], dtype=np.float32)
        link = (matrix @ matrix.T) / np.outer(sizes, sizes)
        np.fill_diagonal(link, -2.0)

        flat = int(np.argmax(link))
        a, b = divmod(flat, len(ids))
        if link[a, b] < threshold:
            break

        keep, drop = ids[min(a, b)], ids[max(a, b)]
        live_sums[keep] = live_sums[keep] + live_sums[drop]
        live_counts[keep] += live_counts[drop]
        alive.discard(drop)
        for old, new in enumerate(mapping):
            if new == drop:
                mapping[old] = keep

    survivors = sorted(alive, key=lambda i: (-live_counts[i], i))
    renumber = {old: new for new, old in enumerate(survivors)}
    return [renumber[mapping[i]] for i in range(k)]


def cluster_vectors(vectors: np.ndarray, threshold: float) -> Clustering:
    """Group unit-length file vectors by subject."""
    n = vectors.shape[0]
    dim = vectors.shape[1] if vectors.ndim == 2 else 0
    sim = cosine_matrix(vectors)

    empty = Clustering(
        labels=np.full(n, UNCLUSTERED, dtype=np.int32),
        sums=np.zeros((0, dim), np.float32),
        counts=np.zeros(0, np.float32),
        sim=sim,
        best_other=np.zeros(n, dtype=np.float32),
    )
    if n == 0:
        return empty

    off_diagonal = sim.copy()
    np.fill_diagonal(off_diagonal, -2.0)
    best_other = off_diagonal.max(axis=1) if n > 1 else np.zeros(n, dtype=np.float32)
    empty.best_other = best_other.astype(np.float32)

    # Seed groups from their most-connected files.
    centrality = np.where(off_diagonal > threshold, off_diagonal, 0.0).sum(axis=1)
    order = np.argsort(-centrality, kind="stable")

    labels, sums, counts = _leader_pass(vectors, order, threshold)
    if not sums:
        return empty

    mapping = _merge(sums, counts, threshold)
    merged = labels.copy()
    for old, new in enumerate(mapping):
        merged[labels == old] = new

    k = max(mapping) + 1
    new_sums = np.zeros((k, dim), dtype=np.float32)
    new_counts = np.zeros(k, dtype=np.float32)
    for cid in range(k):
        members = np.flatnonzero(merged == cid)
        if members.size:
            new_sums[cid] = vectors[members].sum(axis=0)
            new_counts[cid] = float(members.size)
    new_counts[new_counts == 0] = 1.0

    return Clustering(
        labels=merged,
        sums=new_sums,
        counts=new_counts,
        sim=sim,
        best_other=best_other.astype(np.float32),
    )
