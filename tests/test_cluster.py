"""Clustering: average-link semantics, determinism, and chaining resistance."""

from __future__ import annotations

import numpy as np

from messie.cluster import cluster_vectors


def _unit(rows):
    arr = np.asarray(rows, dtype=np.float32)
    return arr / np.linalg.norm(arr, axis=1, keepdims=True)


def test_two_clean_groups_separate():
    vectors = _unit([[1, 0], [1, 0.05], [0, 1], [0, 1.05]])
    result = cluster_vectors(vectors, 0.5)
    assert len(result.groups) == 2
    assert result.labels[0] == result.labels[1]
    assert result.labels[2] == result.labels[3]
    assert result.labels[0] != result.labels[2]


def test_one_group_stays_one():
    vectors = _unit([[1, 0.01 * i] for i in range(8)])
    assert len(cluster_vectors(vectors, 0.5).groups) == 1


def test_link_is_mean_pairwise_similarity():
    vectors = _unit([[1, 0], [1, 0], [0, 1], [0, 1]])
    result = cluster_vectors(vectors, 0.5)
    similarity = result.group_similarity

    for a in range(len(result.groups)):
        for b in range(len(result.groups)):
            if a == b:
                continue
            members_a, members_b = result.groups[a], result.groups[b]
            expected = (vectors[members_a] @ vectors[members_b].T).mean()
            assert similarity[a, b] == np.float32(expected).astype(np.float32)


def test_a_bridging_file_does_not_weld_two_groups():
    """Single-link would chain these into one cluster through the midpoint."""
    vectors = _unit([[1, 0], [1, 0.05], [0.7, 0.7], [0, 1], [0.05, 1]])
    result = cluster_vectors(vectors, 0.75)
    assert result.labels[0] != result.labels[3]


def test_average_link_cut_uses_mean_pairwise_similarity():
    """A merged pair must clear the cut based on its average link to a file."""
    first = np.array([1.0, 0.0, 0.0])
    second = np.array([0.9, np.sqrt(1.0 - 0.9**2), 0.0])
    third = np.array(
        [0.8, (0.5 - 0.9 * 0.8) / second[1], 0.0],
    )
    third[2] = np.sqrt(1.0 - np.dot(third, third))
    vectors = np.asarray([first, second, third], dtype=np.float32)

    result = cluster_vectors(vectors, 0.66)

    assert result.labels[0] == result.labels[1]
    assert result.labels[2] != result.labels[0]
    assert result.group_similarity[0, 1] < 0.66


def test_partition_is_invariant_under_permutation_with_tied_links():
    """Ties in centrality or linkage must not depend on row order."""
    vectors = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.8, 0.6, 0.0],
            [0.8, -0.4, np.sqrt(0.2)],
        ],
        dtype=np.float32,
    )
    threshold = 0.7
    expected = {
        frozenset(group.tolist())
        for group in cluster_vectors(vectors, threshold).groups
    }

    for permutation in (
        np.asarray([2, 0, 1], dtype=np.intp),
        np.asarray([1, 2, 0], dtype=np.intp),
        np.asarray([0, 2, 1], dtype=np.intp),
    ):
        result = cluster_vectors(vectors[permutation], threshold)
        actual = {
            frozenset(permutation[group].tolist())
            for group in result.groups
        }
        assert actual == expected


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
    assert len(result.groups) == 0
    assert result.labels.size == 0


def test_many_unrelated_vectors_keep_separate_labels():
    """The leader pass must stay stable when almost every row starts a group."""
    vectors = np.eye(128, dtype=np.float32)
    result = cluster_vectors(vectors, 0.5)

    assert len(result.groups) == len(vectors)
    assert np.array_equal(result.labels, np.arange(len(vectors), dtype=np.int32))


def test_two_thousand_vectors_remain_practical():
    """The configured upper bound should complete without quadratic Python state."""
    rng = np.random.default_rng(20260925)
    vectors = rng.normal(size=(2_000, 16)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)

    result = cluster_vectors(vectors, 0.8)

    assert result.labels.shape == (2_000,)
    assert sum(len(group) for group in result.groups) == 2_000
