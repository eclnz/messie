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


def _nearest_neighbour_chain(
    similarity: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Build an average-linkage dendrogram with a nearest-neighbour chain.

    ``similarity`` contains the pairwise cosine similarities between the
    non-zero vectors.  The returned arrays describe the internal nodes of the
    dendrogram: each node joins ``left[node]`` and ``right[node]`` at
    ``height[node]``.  Average linkage is reducible, so the nearest-neighbour
    chain algorithm gives the same hierarchy as repeatedly selecting the
    highest average-link pair while using only O(n²) work and storage.

    The chain's tie-breaking is based on the smallest leaf index.  Callers
    sort leaves by their vector values first, which makes those indices stable
    when the input rows are permuted.
    """
    n_leaves = similarity.shape[0]
    n_nodes = max(1, 2 * n_leaves - 1)
    matrix = np.full((n_nodes, n_nodes), -np.inf, dtype=np.float32)
    matrix[:n_leaves, :n_leaves] = similarity

    sizes = np.zeros(n_nodes, dtype=np.int32)
    sizes[:n_leaves] = 1
    # The key is the smallest original leaf in a cluster.  It is unique for
    # distinct clusters and gives a stable tie-break independent of merge IDs.
    keys = np.full(n_nodes, n_leaves, dtype=np.int32)
    keys[:n_leaves] = np.arange(n_leaves, dtype=np.int32)
    active = np.zeros(n_nodes, dtype=bool)
    active[:n_leaves] = True

    left = np.full(n_nodes, -1, dtype=np.int32)
    right = np.full(n_nodes, -1, dtype=np.int32)
    height = np.full(n_nodes, -np.inf, dtype=np.float32)
    chain: list[int] = []
    merges = 0
    n_active = n_leaves

    def nearest(cluster: int) -> int:
        candidates = np.flatnonzero(active)
        candidates = candidates[candidates != cluster]
        scores = matrix[cluster, candidates]
        best_score = scores.max()
        tied = candidates[scores == best_score]
        # keys are unique while clusters are active.  The ID fallback keeps
        # this total and deterministic even for malformed duplicate inputs.
        return min((int(candidate) for candidate in tied), key=lambda item: (keys[item], item))

    while n_active > 1:
        if not chain:
            candidates = np.flatnonzero(active)
            chain.append(
                min((int(item) for item in candidates), key=lambda item: (keys[item], item))
            )

        neighbour = nearest(chain[-1])
        if len(chain) >= 2 and neighbour == chain[-2]:
            first, second = chain[-2:]
            node = n_leaves + merges
            total = sizes[first] + sizes[second]
            others = np.flatnonzero(active)
            others = others[(others != first) & (others != second)]

            left[node] = first
            right[node] = second
            height[node] = matrix[first, second]
            sizes[node] = total
            keys[node] = min(keys[first], keys[second])
            if others.size:
                weight_first = np.float32(sizes[first])
                weight_second = np.float32(sizes[second])
                denominator = np.float32(total)
                matrix[node, others] = (
                    weight_first * matrix[first, others]
                    + weight_second * matrix[second, others]
                ) / denominator
                matrix[others, node] = matrix[node, others]

            active[first] = False
            active[second] = False
            active[node] = True
            merges += 1
            n_active -= 1
            chain = chain[:-2]
        else:
            chain.append(neighbour)

    root = n_leaves + merges - 1
    return left, right, height, root


def _cut_dendrogram(
    left: np.ndarray,
    right: np.ndarray,
    height: np.ndarray,
    root: int,
    n_leaves: int,
    threshold: float,
) -> np.ndarray:
    """Return stable group labels for a similarity threshold cut."""
    labels = np.full(n_leaves, UNCLUSTERED, dtype=np.int32)
    if n_leaves == 0:
        return labels
    if n_leaves == 1:
        labels[0] = 0
        return labels

    groups: list[list[int]] = []
    pending = [root]
    while pending:
        node = pending.pop()
        if node < n_leaves or height[node] >= threshold:
            leaves: list[int] = []
            descendants = [node]
            while descendants:
                descendant = descendants.pop()
                if descendant < n_leaves:
                    leaves.append(descendant)
                else:
                    descendants.append(int(left[descendant]))
                    descendants.append(int(right[descendant]))
            groups.append(leaves)
        else:
            pending.append(int(left[node]))
            pending.append(int(right[node]))

    groups.sort(key=lambda members: min(members))
    for label, members in enumerate(groups):
        labels[np.asarray(members, dtype=np.intp)] = label
    return labels


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

    valid = np.flatnonzero(np.any(vectors != 0, axis=1))
    if valid.size == 0:
        return _clustering(labels, vectors, similarity, closest)

    # Sort rows by value before clustering.  The internal leaf index is then
    # independent of the caller's file ordering (apart from indistinguishable
    # duplicate vectors, whose identities cannot be recovered from values).
    valid_vectors = vectors[valid]
    order = np.lexsort((-valid_vectors[:, ::-1]).T)
    original_indices = valid[order]
    valid_similarity = similarity[np.ix_(original_indices, original_indices)]

    left, right, height, root = _nearest_neighbour_chain(valid_similarity)
    sorted_labels = _cut_dendrogram(
        left,
        right,
        height,
        root,
        len(original_indices),
        threshold,
    )
    labels[original_indices] = sorted_labels
    return _clustering(labels, vectors, similarity, closest)
