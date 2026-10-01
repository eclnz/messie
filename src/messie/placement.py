"""Optional, content-based checks for folders placed in the wrong subtree."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import numpy as np

from messie.paths import display_path
from messie.result import Finding

if TYPE_CHECKING:
    from messie.analyze import VectorRecord
    from messie.scan import DirContents


_MAX_SAMPLES = 96
_MAX_TOPICS = 6
_MIN_FILES = 3
_MIN_ADVANTAGE = 0.08
_MIN_LOCAL_GAP = 0.40
_MIN_SUPPORT = 0.60
_NAME_WEIGHT = 0.35


@dataclass(frozen=True)
class FolderProfile:
    """A small set of topics, preserving their share of a subtree."""

    vectors: np.ndarray
    weights: np.ndarray
    files: int
    examples: tuple[str, ...]


@dataclass(frozen=True)
class PlacementEvidence:
    """Local evidence for an out-of-place folder and an optional related folder."""

    related_folder: Path | None
    subtree_files: int
    current_fit: float
    expected_fit: float
    local_gap: float
    supported_fraction: float
    related_fit: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "related_folder": display_path(self.related_folder) if self.related_folder else None,
            "subtree_files": self.subtree_files,
            "current_fit": round(self.current_fit, 3),
            "expected_fit": round(self.expected_fit, 3),
            "local_gap": round(self.local_gap, 3),
            "supported_fraction": round(self.supported_fraction, 3),
            "related_fit": (
                round(self.related_fit, 3) if self.related_fit is not None else None
            ),
        }


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1e-8 else np.zeros_like(vector)


def _profile(evidence: list[tuple[np.ndarray, str]]) -> FolderProfile | None:
    if len(evidence) < _MIN_FILES:
        return None
    total_files = len(evidence)
    if len(evidence) > _MAX_SAMPLES:
        step = len(evidence) / _MAX_SAMPLES
        evidence = [evidence[int(i * step)] for i in range(_MAX_SAMPLES)]

    vectors = np.stack([vector for vector, _ in evidence])
    count = min(_MAX_TOPICS, max(1, len(evidence) // _MIN_FILES))
    # Start at the most representative file, then preserve distant subjects.
    first = int(np.argmax(vectors @ _unit(vectors.mean(axis=0))))
    seeds = [first]
    while len(seeds) < count:
        nearest = (vectors @ vectors[seeds].T).max(axis=1)
        nearest[seeds] = 1.0
        seeds.append(int(np.argmin(nearest)))
    labels = np.argmax(vectors @ vectors[seeds].T, axis=1)
    topics: list[np.ndarray] = []
    weights: list[float] = []
    examples: list[str] = []
    for index in range(len(seeds)):
        members = np.flatnonzero(labels == index)
        if not members.size:
            continue
        topic = _unit(vectors[members].mean(axis=0))
        topics.append(topic)
        weights.append(float(members.size / len(evidence)))
        representative = int(members[np.argmax(vectors[members] @ topic)])
        examples.append(evidence[representative][1])
    return FolderProfile(np.stack(topics), np.asarray(weights), total_files, tuple(examples))


def _direct_evidence(
    contents: list[DirContents],
    records: dict[Path, VectorRecord],
    name_vectors: dict[Path, np.ndarray],
) -> tuple[
    dict[Path, list[tuple[np.ndarray, str]]],
    dict[Path, list[tuple[np.ndarray, str]]],
]:
    evidence: dict[Path, list[tuple[np.ndarray, str]]] = {}
    content: dict[Path, list[tuple[np.ndarray, str]]] = {}
    for folder in contents:
        path = folder.path.resolve()
        record = records.get(path)
        if record is None:
            continue
        evidence[path] = []
        content[path] = []
        for i, file in enumerate(folder.files):
            if not record.topical[i] or not record.vectors[i].any():
                continue
            vector = record.vectors[i]
            name = name_vectors[file.path]
            combined = _unit(np.concatenate((
                math.sqrt(1.0 - _NAME_WEIGHT) * vector,
                math.sqrt(_NAME_WEIGHT) * name,
            )))
            evidence[path].append((combined, str(file.path)))
            content[path].append((vector, str(file.path)))
    return evidence, content


def _fit(query: FolderProfile, reference: FolderProfile) -> np.ndarray:
    """Best reference topic for each query topic; reference size gives no bonus."""
    return (query.vectors @ reference.vectors.T).max(axis=1)


def _coherence(evidence: list[tuple[np.ndarray, str]]) -> float:
    """A parent with several subjects offers weaker evidence of an outlier."""
    if len(evidence) < _MIN_FILES:
        return 0.0
    if len(evidence) > _MAX_SAMPLES:
        step = len(evidence) / _MAX_SAMPLES
        evidence = [evidence[int(i * step)] for i in range(_MAX_SAMPLES)]
    vectors = np.stack([vector for vector, _ in evidence])
    scores = vectors @ vectors.T
    pairwise = float((scores.sum() - np.trace(scores)) /
                     (len(vectors) * (len(vectors) - 1)))
    np.fill_diagonal(scores, -np.inf)
    nearest = float(scores.max(axis=1).mean())
    return max(0.0, (pairwise + nearest) / 2)


def _repeated_child_role(
    path: Path,
    profiles: dict[Path, FolderProfile],
    direct_profiles: dict[Path, FolderProfile],
    cluster_threshold: float,
) -> bool:
    """Recognize a subject repeated under parallel parents without using names."""
    parent = path.parent
    parent_profile = direct_profiles.get(parent)
    if parent_profile is None:
        return False
    query = profiles[path]
    role_fit = max(0.60, cluster_threshold + 0.25)
    for other, other_profile in profiles.items():
        if other == path or other.parent == parent or other.parent.parent != parent.parent:
            continue
        other_parent = direct_profiles.get(other.parent)
        if other_parent is None:
            continue
        if float(query.weights @ _fit(query, other_profile)) < role_fit:
            continue
        if float(other_profile.weights @ _fit(other_profile, query)) < role_fit:
            continue
        if float(other_profile.weights @ _fit(other_profile, other_parent)) >= role_fit:
            continue
        return True
    return False


def _stack_profiles(profiles: dict[Path, FolderProfile]) -> tuple[np.ndarray, dict[Path, slice]]:
    """Pack topic vectors so one matrix multiply can compare all destinations."""
    spans: dict[Path, slice] = {}
    offset = 0
    for path, profile in profiles.items():
        end = offset + len(profile.vectors)
        spans[path] = slice(offset, end)
        offset = end
    return np.concatenate([profile.vectors for profile in profiles.values()]), spans


def _branch_groups(
    branches: list[Path], profiles: dict[Path, FolderProfile]
) -> dict[Path, int]:
    """Group similar siblings so repeated subjects each get one vote."""
    representatives: list[np.ndarray] = []
    groups: dict[Path, int] = {}
    for path in branches:
        profile = profiles[path]
        representative = _unit(profile.weights @ profile.vectors)
        matches = [float(representative @ other) for other in representatives]
        if not matches or max(matches) < 0.75:
            groups[path] = len(representatives)
            representatives.append(representative)
        else:
            groups[path] = int(np.argmax(matches))
    return groups


def folder_placement_findings(
    contents: list[DirContents],
    records: dict[Path, VectorRecord],
    name_vectors: dict[Path, np.ndarray],
    cluster_threshold: float,
    progress: Callable[[int, int, Path], None] | None = None,
) -> dict[Path, Finding]:
    """Find locally unusual subtrees; use other locations only as explanations."""
    paths = [folder.path.resolve() for folder in contents]
    if not paths:
        return {}
    report = progress or (lambda _done, _total, _path: None)
    progress_total = 3 * len(paths)
    report(0, progress_total, paths[0])
    if len(paths) < 3:
        report(progress_total, progress_total, paths[0])
        return {}
    root = paths[0]
    # Build the scanned tree once. Repeated Path ancestry checks dominate a
    # broad scan with hundreds of folders and many destination comparisons.
    subtrees: dict[Path, list[Path]] = {path: [path] for path in paths}
    for path in paths:
        for ancestor in path.parents:
            if ancestor in subtrees:
                subtrees[ancestor].append(path)
    subtree_sets = {path: set(children) for path, children in subtrees.items()}
    direct, content_direct = _direct_evidence(contents, records, name_vectors)
    profiles: dict[Path, FolderProfile] = {}
    content_profiles: dict[Path, FolderProfile] = {}
    for done, path in enumerate(paths, start=1):
        gathered = [
            item
            for child in subtrees[path]
            for item in direct.get(child, ())
        ]
        profile = _profile(gathered)
        if profile is not None:
            profiles[path] = profile
            content_profile = _profile([
                item
                for child in subtrees[path]
                for item in content_direct.get(child, ())
            ])
            assert content_profile is not None
            content_profiles[path] = content_profile
        report(done, progress_total, path)

    if not profiles:
        report(progress_total, progress_total, root)
        return {}
    topic_vectors, topic_spans = _stack_profiles(profiles)
    content_vectors, content_spans = _stack_profiles(content_profiles)
    direct_profiles = {
        path: profile
        for path, evidence in direct.items()
        if (profile := _profile(evidence)) is not None
    }
    children: dict[Path, list[Path]] = {path: [] for path in paths}
    for path in paths[1:]:
        if path.parent in children and path in profiles:
            children[path.parent].append(path)
    branch_groups = {
        parent: _branch_groups(branches, profiles)
        for parent, branches in children.items() if branches
    }
    local_fits: dict[Path, np.ndarray] = {}
    local_sizes: dict[Path, int] = {}
    for done, path in enumerate(paths, start=1):
        if path in profiles and path.parent in subtrees:
            nearby = [
                item
                for child in subtrees[path.parent]
                if child not in subtree_sets[path]
                for item in direct.get(child, ())
            ]
            current = _profile(nearby)
            if current is not None:
                local_fits[path] = _fit(profiles[path], current)
                local_sizes[path] = current.files
        report(len(paths) + done, progress_total, path)
    findings: dict[Path, Finding] = {}
    for done, path in enumerate(paths, start=1):
        report(2 * len(paths) + done, progress_total, path)
        if path not in local_fits:
            continue
        parent = path.parent
        query = profiles[path]
        # A few incidental files beside a substantial subtree cannot establish
        # what belongs at its current location.
        if local_sizes[path] < query.files / 2:
            continue
        own_fit = local_fits[path]
        current_fit = float(query.weights @ own_fit)
        peer_groups: dict[int, list[float]] = {}
        for peer in children[parent]:
            if peer == path or peer not in local_fits:
                continue
            if local_sizes[peer] < profiles[peer].files / 2:
                continue
            peer_groups.setdefault(branch_groups[parent][peer], []).append(
                float(profiles[peer].weights @ local_fits[peer])
            )
        peer_fits = [float(np.median(group)) for group in peer_groups.values()]
        parent_evidence = direct.get(parent, [])
        if not parent_evidence and len(peer_fits) < 2:
            # Two unlike branches with no files in their parent give no basis
            # for deciding which, if either, is out of place.
            continue
        if peer_fits:
            expected_fit = float(np.median(peer_fits))
        else:
            expected_fit = _coherence(parent_evidence)
        expected_fit -= 0.08 * math.log2(len(set(branch_groups[parent].values())))
        local_gap = expected_fit - current_fit
        supported = float(query.weights[
            own_fit <= expected_fit - _MIN_LOCAL_GAP / 2
        ].sum())
        if local_gap < _MIN_LOCAL_GAP or supported < _MIN_SUPPORT:
            continue
        # Similar departures under sibling parents are a recurring layout,
        # rather than evidence that one of those children is misplaced.
        if _repeated_child_role(path, profiles, direct_profiles, cluster_threshold):
            continue

        content_query = content_profiles[path]
        topic_scores = query.vectors @ topic_vectors.T
        content_scores = content_query.vectors @ content_vectors.T
        best: tuple[float, Path] | None = None
        for destination, reference in profiles.items():
            if destination in subtree_sets[path] or path in subtree_sets[destination]:
                continue
            pair_scores = topic_scores[:, topic_spans[destination]]
            alternative = pair_scores.max(axis=1)
            fit = float(query.weights @ alternative)
            if fit < cluster_threshold or fit - current_fit < _MIN_ADVANTAGE:
                continue
            alternative_support = float(query.weights[
                alternative - own_fit >= _MIN_ADVANTAGE
            ].sum())
            if alternative_support < _MIN_SUPPORT:
                continue
            content_fit = float(content_query.weights @
                                content_scores[:, content_spans[destination]].max(axis=1))
            if content_fit < cluster_threshold:
                continue
            destination_coverage = float(reference.weights[
                pair_scores.max(axis=0) >= cluster_threshold
            ].sum())
            if destination_coverage < _MIN_SUPPORT:
                continue
            if best is None or fit > best[0]:
                best = (fit, destination)
        severity = min(1.0, max(0.0, local_gap / max(0.30, cluster_threshold)))
        related = best[1] if best else None
        detail = "Its contents differ from the pattern around its parent folder."
        if related is not None:
            detail += f" Related contents appear in {display_path(related)}."
        findings[path] = Finding(
            code="folder_placement",
            severity=severity,
            headline="This folder looks out of place among its surroundings.",
            detail=detail,
            examples=list(query.examples[:3]),
            data=PlacementEvidence(
                related_folder=related,
                subtree_files=query.files,
                current_fit=current_fit,
                expected_fit=expected_fit,
                local_gap=local_gap,
                supported_fraction=supported,
                related_fit=best[0] if best else None,
            ),
        )
    return findings
