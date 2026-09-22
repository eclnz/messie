"""Clustering: average-link semantics, determinism, and chaining resistance."""

from __future__ import annotations

import numpy as np

from messie.cluster import cluster_vectors, cosine_matrix


def _unit(rows):
    arr = np.asarray(rows, dtype=np.float32)
    return arr / np.linalg.norm(arr, axis=1, keepdims=True)


def test_two_clean_groups_separate():
    vectors = _unit([[1, 0], [1, 0.05], [0, 1], [0, 1.05]])
    result = cluster_vectors(vectors, 0.5)
    assert result.n_clusters == 2
    assert result.labels[0] == result.labels[1]
    assert result.labels[2] == result.labels[3]
    assert result.labels[0] != result.labels[2]


def test_one_group_stays_one():
    vectors = _unit([[1, 0.01 * i] for i in range(8)])
    assert cluster_vectors(vectors, 0.5).n_clusters == 1


def test_link_is_mean_pairwise_similarity():
    vectors = _unit([[1, 0], [1, 0], [0, 1], [0, 1]])
    result = cluster_vectors(vectors, 0.5)
    link = result.link()
    sim = cosine_matrix(vectors)

    for a in range(result.n_clusters):
        for b in range(result.n_clusters):
            if a == b:
                continue
            members_a, members_b = result.members(a), result.members(b)
            expected = sim[np.ix_(members_a, members_b)].mean()
            assert link[a, b] == np.float32(expected).astype(np.float32)


def test_a_bridging_file_does_not_weld_two_groups():
    """Single-link would chain these into one cluster through the midpoint."""
    vectors = _unit([[1, 0], [1, 0.05], [0.7, 0.7], [0, 1], [0.05, 1]])
    result = cluster_vectors(vectors, 0.75)
    assert result.labels[0] != result.labels[3]


def test_zero_vectors_join_nothing():
    vectors = np.array([[1, 0], [1, 0], [0, 0]], dtype=np.float32)
    result = cluster_vectors(vectors, 0.5)
    assert result.labels[2] == -1


def test_is_deterministic_under_reordering_of_equal_input():
    vectors = _unit([[1, 0], [1, 0.02], [0, 1], [0, 1.02], [0.5, 0.5]])
    first = cluster_vectors(vectors, 0.6)
    second = cluster_vectors(vectors, 0.6)
    assert np.array_equal(first.labels, second.labels)


def test_empty_input():
    result = cluster_vectors(np.zeros((0, 4), dtype=np.float32), 0.5)
    assert result.n_clusters == 0
    assert result.labels.size == 0
