"""Optional, content-based checks for folders placed in the wrong subtree."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import numpy as np

from messie.result import Finding

if TYPE_CHECKING:
    from messie.analyze import VectorRecord
    from messie.scan import DirContents


_MAX_SAMPLES = 96
_MAX_TOPICS = 6
_MIN_FILES = 3
_MIN_ADVANTAGE = 0.08
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
    """Measured support for one proposed parent folder."""

    suggested_parent: Path
    subtree_files: int
    current_fit: float
    alternative_fit: float
    advantage: float
    supported_fraction: float

    def to_dict(self) -> dict[str, object]:
        return {
            "suggested_parent": str(self.suggested_parent),
            "subtree_files": self.subtree_files,
            "current_fit": round(self.current_fit, 3),
            "alternative_fit": round(self.alternative_fit, 3),
            "advantage": round(self.advantage, 3),
            "supported_fraction": round(self.supported_fraction, 3),
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


def _stack_profiles(profiles: dict[Path, FolderProfile]) -> tuple[np.ndarray, dict[Path, slice]]:
    """Pack topic vectors so one matrix multiply can compare all destinations."""
    spans: dict[Path, slice] = {}
    offset = 0
    for path, profile in profiles.items():
        end = offset + len(profile.vectors)
        spans[path] = slice(offset, end)
        offset = end
    return np.concatenate([profile.vectors for profile in profiles.values()]), spans


def folder_placement_findings(
    contents: list[DirContents],
    records: dict[Path, VectorRecord],
    name_vectors: dict[Path, np.ndarray],
    cluster_threshold: float,
    progress: Callable[[int, int, Path], None] | None = None,
) -> dict[Path, Finding]:
    """Find subtrees whose topics fit another location markedly better."""
    paths = [folder.path.resolve() for folder in contents]
    if not paths:
        return {}
    report = progress or (lambda _done, _total, _path: None)
    report(0, len(paths), paths[0])
    if len(paths) < 3:
        report(len(paths), len(paths), paths[0])
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
    for path in paths:
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

    if not profiles:
        report(len(paths), len(paths), root)
        return {}
    topic_vectors, topic_spans = _stack_profiles(profiles)
    content_vectors, content_spans = _stack_profiles(content_profiles)
    findings: dict[Path, Finding] = {}
    for done, path in enumerate(paths, start=1):
        report(done, len(paths), path)
        if path == root or path not in profiles:
            continue
        parent = path.parent
        if parent not in paths:
            continue
        # The current location consists of everything beside this subtree.
        candidate_subtree = subtree_sets[path]
        nearby = [
            (child, item)
            for child in subtrees[parent]
            if child not in candidate_subtree
            for item in direct.get(child, ())
        ]
        current = _profile([item for _, item in nearby])
        if current is None:
            continue
        query = profiles[path]
        # A few incidental files beside a substantial subtree cannot establish
        # what belongs at its current location.
        if current.files < query.files / 2:
            continue
        content_query = content_profiles[path]
        topic_scores = query.vectors @ topic_vectors.T
        content_scores = content_query.vectors @ content_vectors.T
        best: tuple[float, Path, np.ndarray, float] | None = None
        best_current_fit: np.ndarray | None = None
        for destination, reference in profiles.items():
            if destination in candidate_subtree or path in subtree_sets[destination]:
                continue
            pair_scores = topic_scores[:, topic_spans[destination]]
            alternative = pair_scores.max(axis=1)
            fit = float(query.weights @ alternative)
            if fit < cluster_threshold:
                continue
            content_reference = content_profiles[destination]
            content_fit = float(content_query.weights @
                                content_scores[:, content_spans[destination]].max(axis=1))
            if content_fit < cluster_threshold:
                continue
            destination_coverage = float(reference.weights[
                pair_scores.max(axis=0) >= cluster_threshold
            ].sum())
            if destination_coverage < _MIN_SUPPORT:
                continue
            # A direct sibling cannot also serve as evidence that the
            # candidate belongs beside it. Deeper descendants of another
            # branch remain part of that branch's current context.
            local_current = current
            if destination.parent == parent:
                destination_subtree = subtree_sets[destination]
                local_current = _profile([
                    item for child, item in nearby if child not in destination_subtree
                ])
                if local_current is None or local_current.files < query.files / 2:
                    continue
            own_fit = _fit(query, local_current)
            improvement = alternative - own_fit
            supported = float(query.weights[improvement >= _MIN_ADVANTAGE].sum())
            if supported < _MIN_SUPPORT:
                continue
            advantage = float(query.weights @ improvement)
            if advantage < _MIN_ADVANTAGE:
                continue
            candidate = (advantage, destination, alternative, supported)
            if best is None or candidate[0] > best[0]:
                best = candidate
                best_current_fit = own_fit
        if best is None:
            continue
        assert best_current_fit is not None
        advantage, destination, alternative, supported = best
        severity = min(1.0, max(0.0, advantage / max(0.20, cluster_threshold)))
        findings[path] = Finding(
            code="folder_placement",
            severity=severity,
            headline="This folder's contents fit better elsewhere in the tree.",
            detail=f"Its contents resemble {destination} more than their current surroundings.",
            examples=list(query.examples[:3]),
            data=PlacementEvidence(
                suggested_parent=destination,
                subtree_files=query.files,
                current_fit=float(query.weights @ best_current_fit),
                alternative_fit=float(query.weights @ alternative),
                advantage=advantage,
                supported_fraction=supported,
            ),
        )
    return findings
