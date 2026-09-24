"Walking a tree and judging every folder in it."

from __future__ import annotations

from collections.abc import Callable
from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import NamedTuple

import numpy as np

from messie.binary_description import describe_binary
from messie.cache import EvidenceCache
from messie.cluster import Clustering, cluster_vectors
from messie.config import DEFAULT_SETTINGS, Settings, Thresholds
from messie.embed import Embedder, get_embedder, normalise
from messie.extract import extract_text
from messie.kinds import Kind, is_textual, kind_phrase
from messie.label import file_terms, format_label, label_clusters
from messie.result import DirAnalysis, Finding, SkipReason, Verdict
from messie.scan import DirContents, FileEntry, read_dir, walk
from messie.signals import run_all
from messie.tokens import name_tokens

__all__ = [
    "DirAnalysis",
    "Progress",
    "ProgressFn",
    "analyze_dir",
    "analyze_tree",
]


@dataclass(frozen=True)
class Progress:
    "Where a tree walk has got to."
    stage: str
    done: int
    total: int
    path: Path | None = None
    files: int = 0


ProgressFn = Callable[[Progress], None]


def _verdict_for(score: float) -> Verdict:
    if score >= 75:
        return Verdict.CHAOTIC
    if score >= 50:
        return Verdict.MESSY
    if score >= 25:
        return Verdict.LIVED_IN
    return Verdict.TIDY


def _score_findings(
    findings: list[Finding], settings: Settings = DEFAULT_SETTINGS
) -> tuple[float, Verdict]:
    """Combine signal severities into an overall score and verdict."""
    residual = 0.0
    for finding in findings:
        weight = settings.signal_weights.get(finding.code, 0.3)
        contribution = max(0.0, min(0.999, weight * finding.severity))
        residual += math.log1p(-contribution)

    score = round(100.0 * (1.0 - math.exp(residual)), 1)
    return score, _verdict_for(score)


class VectorRecord(NamedTuple):
    """What vectorising one folder produced."""

    texts: list[str]
    vectors: np.ndarray
    topical: np.ndarray
    terms: list[Counter]


@dataclass
class SignalContext:
    """Evidence and settings a signal needs while judging one folder."""

    path: Path
    settings: Settings
    thresholds: Thresholds
    embedder: str
    files: list[FileEntry]
    texts: list[str]
    terms: list[Counter]
    vectors: np.ndarray
    topical: np.ndarray
    clustering: Clustering
    cluster_labels: dict[int, list[str]]
    child_profiles: dict[Path, np.ndarray]
    subdirs: list[Path]
    truncated: int

    @property
    def n_files(self) -> int:
        return len(self.files)

    def meaningful_clusters(self) -> list[int]:
        floor = max(
            self.settings.meaningful_cluster_min,
            int(self.settings.meaningful_cluster_frac * self.n_files),
        )
        return [
            cluster
            for cluster, members in enumerate(self.clustering.groups)
            if len(members) >= floor
        ]

    def members(self, cluster: int) -> list[int]:
        return self.clustering.groups[cluster].tolist()

    def label_of(self, cluster: int) -> str:
        return format_label(self.cluster_labels.get(cluster, []))

    def names(self, indices: list[int], limit: int = 3) -> list[str]:
        return [self.files[index].name for index in indices[:limit]]

    def mtime_span(self, indices: list[int]) -> tuple[float, float]:
        if not indices:
            return (0.0, 0.0)
        times = [self.files[index].mtime for index in indices]
        return (min(times), max(times))


class Mix(NamedTuple):
    """How much the text, name and kind vectors each count."""

    text: float
    name: float
    kind: float


_MIX_RICH = Mix(0.75, 0.20, 0.05)
_MIX_THIN = Mix(0.45, 0.40, 0.15)
_MIX_NAME = Mix(0.00, 0.80, 0.20)
_MIX_KIND = Mix(0.00, 0.00, 1.00)
_MIX_META = Mix(0.85, 0.15, 0.00)
_WORDS_RE = re.compile(r"[^\W\d_]{3,}")
_COMMON_NAME_SHARE = 0.7


def _name_phrases(files: list[FileEntry]) -> list[str]:
    token_lists = [name_tokens(file.stem) for file in files]
    common: set[str] = set()
    if len(files) >= 5:
        frequency: Counter[str] = Counter()
        for tokens in token_lists:
            frequency.update(set(tokens))
        cutoff = _COMMON_NAME_SHARE * len(files)
        common = {token for token, count in frequency.items() if count >= cutoff}
    return [" ".join(token for token in tokens if token not in common) for tokens in token_lists]


def _mix_for(entry: FileEntry, text: str, name: str, settings: Settings) -> Mix:
    if text.strip() and not is_textual(entry.kind) and _WORDS_RE.search(text):
        return _MIX_META
    if text.strip() and len(text) >= settings.min_text_chars:
        return _MIX_RICH
    if text.strip():
        return _MIX_THIN
    if name.strip():
        return _MIX_NAME
    return _MIX_KIND


def vectorize(
    files: list[FileEntry],
    *,
    embedder: Embedder,
    settings: Settings = DEFAULT_SETTINGS,
    cache: EvidenceCache | None = None,
) -> VectorRecord:
    """Turn scanned files into the evidence needed by signals."""
    texts: list[str] = []
    for file in files:
        text = cache.get(file) if cache is not None else None
        if text is None:
            text = extract_text(file, settings) or describe_binary(file, settings)
            if cache is not None:
                cache.put(file, text)
        texts.append(text)
    names = _name_phrases(files)
    text_vectors = embedder.encode(texts)
    name_vectors = embedder.encode(names)
    kind_vectors = embedder.encode([kind_phrase(file.kind) for file in files])
    vectors = np.zeros((len(files), text_vectors.shape[1]), dtype=np.float32)
    topical = np.zeros(len(files), dtype=bool)

    for index, (entry, text, name) in enumerate(zip(files, texts, names, strict=True)):
        if entry.kind is Kind.JUNK or entry.size == 0:
            continue
        mix = _mix_for(entry, text, name, settings)
        vectors[index] = (
            mix.text * text_vectors[index]
            + mix.name * name_vectors[index]
            + mix.kind * kind_vectors[index]
        )
        topical[index] = bool(text.strip()) or bool(name.strip())

    terms = [file_terms(file.stem, text) for file, text in zip(files, texts, strict=True)]
    return VectorRecord(texts, normalise(vectors), topical, terms)


def profile_of(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return np.zeros(0, dtype=np.float32)
    return vectors.mean(axis=0).astype(np.float32)


def profile(
    files: list[FileEntry],
    *,
    embedder: Embedder,
    settings: Settings = DEFAULT_SETTINGS,
    cache: EvidenceCache | None = None,
) -> np.ndarray:
    if not files:
        return np.zeros(0, dtype=np.float32)
    return profile_of(vectorize(files, embedder=embedder, settings=settings, cache=cache).vectors)


def analyze(
    contents: DirContents,
    *,
    embedder: Embedder | None = None,
    settings: Settings = DEFAULT_SETTINGS,
    child_profiles: dict[Path, np.ndarray] | None = None,
    precomputed: VectorRecord | None = None,
) -> DirAnalysis:
    """Judge scanned folder contents, reusing vectors when supplied."""
    embedder = embedder or get_embedder()
    if len(contents.files) < settings.min_files_to_judge:
        return DirAnalysis(
            path=contents.path,
            embedder=embedder.name,
            n_files=len(contents.files),
            truncated=contents.truncated,
            judged=False,
            skip_reason=SkipReason.TOO_FEW_FILES,
        )

    thresholds = Thresholds.derive(
        embedder.scale, settings, settings.cluster_threshold_override
    )
    record = precomputed or vectorize(contents.files, embedder=embedder, settings=settings)
    clustering = cluster_vectors(record.vectors, thresholds.cluster)
    context = SignalContext(
        path=contents.path,
        settings=settings,
        thresholds=thresholds,
        embedder=embedder.name,
        files=list(contents.files),
        texts=record.texts,
        terms=record.terms,
        vectors=record.vectors,
        topical=record.topical,
        clustering=clustering,
        cluster_labels=label_clusters(clustering.labels, record.terms, len(clustering.groups)),
        child_profiles=child_profiles or {},
        subdirs=list(contents.subdirs),
        truncated=contents.truncated,
    )
    signal_run = run_all(context)
    score, verdict = _score_findings(signal_run.findings, settings)
    return DirAnalysis(
        path=context.path,
        embedder=context.embedder,
        n_files=context.n_files,
        truncated=context.truncated,
        clusters=len(clustering.groups),
        meaningful_clusters=len(context.meaningful_clusters()),
        findings=signal_run.findings,
        failed_signals=signal_run.failed,
        score=score,
        verdict=verdict,
    )


def _descendant_profiles(
    root: Path,
    settings: Settings,
    embedder: Embedder,
    cache: EvidenceCache,
) -> dict[Path, np.ndarray]:
    """Profiles of meaningful folders below ``root`` for misfiling checks."""
    profiles: dict[Path, np.ndarray] = {}
    for contents in walk(root, settings):
        path = contents.path.resolve()
        if path == root or len(contents.files) < settings.meaningful_cluster_min:
            continue
        profiles[path] = profile(
            contents.files, embedder=embedder, settings=settings, cache=cache
        )
    return profiles


def analyze_dir(
    path: Path,
    settings: Settings = DEFAULT_SETTINGS,
    embedder: Embedder | None = None,
) -> DirAnalysis:
    "Judge a single folder, ignoring what is in its subfolders."
    embedder = embedder or get_embedder()
    root = path.expanduser().resolve()
    with EvidenceCache(settings) as cache:
        contents = read_dir(root, settings)
        record = (
            vectorize(contents.files, embedder=embedder, settings=settings, cache=cache)
            if len(contents.files) >= settings.min_files_to_judge
            else None
        )
        return analyze(
            contents,
            embedder=embedder,
            settings=settings,
            child_profiles=_descendant_profiles(root, settings, embedder, cache),
            precomputed=record,
        )


def _vectorized_profiles(
    contents: list[DirContents],
    settings: Settings,
    embedder: Embedder,
    report: ProgressFn,
    cache: EvidenceCache,
) -> tuple[dict[Path, VectorRecord], dict[Path, np.ndarray]]:
    """Vectorise each meaningful folder once and derive its profile."""
    records: dict[Path, VectorRecord] = {}
    profiles: dict[Path, np.ndarray] = {}
    for done, folder in enumerate(contents, start=1):
        report(Progress("read", done, len(contents), folder.path, len(folder.files)))
        if len(folder.files) < settings.meaningful_cluster_min:
            continue
        path = folder.path.resolve()
        records[path] = vectorize(
            folder.files, embedder=embedder, settings=settings, cache=cache
        )
        profiles[path] = profile_of(records[path].vectors)
    return records, profiles


def _profiles_by_ancestor(
    contents: list[DirContents], profiles: dict[Path, np.ndarray]
) -> dict[Path, dict[Path, np.ndarray]]:
    """Give every folder the profiles of all meaningful folders below it."""
    paths = {folder.path.resolve() for folder in contents}
    descendants: dict[Path, dict[Path, np.ndarray]] = {}
    for descendant, profile in profiles.items():
        for ancestor in descendant.parents:
            if ancestor in paths:
                descendants.setdefault(ancestor, {})[descendant] = profile
    return descendants


def _judge_tree(
    contents: list[DirContents],
    settings: Settings,
    embedder: Embedder,
    records: dict[Path, VectorRecord],
    descendants: dict[Path, dict[Path, np.ndarray]],
    report: ProgressFn,
) -> list[DirAnalysis]:
    """Judge every scanned folder using already-computed vector records."""
    results = []
    for done, folder in enumerate(contents, start=1):
        report(Progress("judge", done, len(contents), folder.path, len(folder.files)))
        path = folder.path.resolve()
        results.append(
            analyze(
                folder,
                embedder=embedder,
                settings=settings,
                child_profiles=descendants.get(path, {}),
                precomputed=records.get(path),
            )
        )
    return sorted(results, key=lambda analysis: (-analysis.score, str(analysis.path)))


def analyze_tree(
    root: Path | str,
    settings: Settings = DEFAULT_SETTINGS,
    embedder: Embedder | None = None,
    progress: ProgressFn | None = None,
) -> list[DirAnalysis]:
    """Judge every folder at or under ``root``, worst first."""
    embedder = embedder or get_embedder()
    report: ProgressFn = progress or (lambda _: None)
    root = Path(root).expanduser().resolve()
    contents = walk(root, settings)
    report(Progress("scan", len(contents), len(contents), root))
    with EvidenceCache(settings) as cache:
        records, profiles = _vectorized_profiles(contents, settings, embedder, report, cache)
        return _judge_tree(
            contents,
            settings,
            embedder,
            records,
            _profiles_by_ancestor(contents, profiles),
            report,
        )
