"Walking a tree and judging every folder in it."

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
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
    """Combine the strongest finding in each signal family."""
    families = {
        "unrelated_topics": "topical_disorder",
        "no_common_thread": "topical_disorder",
        "strays": "topical_disorder",
        "time_strata": "topical_disorder",
    }
    strongest: dict[str, float] = {}
    for finding in findings:
        weight = settings.signal_weights.get(finding.code, 0.3)
        contribution = max(0.0, min(0.999, weight * finding.severity))
        family = families.get(finding.code, finding.code)
        strongest[family] = max(strongest.get(family, 0.0), contribution)

    residual = 0.0
    for contribution in strongest.values():
        residual += math.log1p(-contribution)

    score = round(100.0 * (1.0 - math.exp(residual)), 1)
    return score, _verdict_for(score)


class VectorRecord(NamedTuple):
    """What vectorising one folder produced."""

    texts: list[str]
    vectors: np.ndarray
    topical: np.ndarray
    terms: list[Counter]


class PreparedRecord(NamedTuple):
    """Extracted and tokenized evidence awaiting embedding."""

    files: list[FileEntry]
    texts: list[str]
    names: list[str]
    kinds: list[str]
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
    if text.strip():
        thin_text = max(0.0, min(1.0, settings.text_weight_thin))
        rich_text = max(0.0, min(1.0, settings.text_weight_rich))
        thin = Mix(thin_text, (1.0 - thin_text) * 8.0 / 11.0,
                   (1.0 - thin_text) * 3.0 / 11.0)
        rich = Mix(rich_text, (1.0 - rich_text) * 4.0 / 5.0,
                   (1.0 - rich_text) * 1.0 / 5.0)
        scale = max(1, settings.min_text_chars)
        progress = min(1.0, len(text) / scale)
        progress = progress * progress * (3.0 - 2.0 * progress)
        return Mix(*(a + (b - a) * progress for a, b in zip(thin, rich, strict=True)))
    if name.strip():
        return _MIX_NAME
    return _MIX_KIND


def _prepare(
    files: list[FileEntry],
    *,
    settings: Settings = DEFAULT_SETTINGS,
    cache: EvidenceCache | None = None,
) -> PreparedRecord:
    image_indices = [index for index, file in enumerate(files) if file.kind is Kind.IMAGE]
    described_images = set(image_indices)
    limit = max(0, settings.image_description_sample)
    if len(image_indices) > limit:
        ordered = sorted(image_indices, key=lambda index: files[index].name)
        if limit:
            step = len(ordered) / limit
            described_images = {ordered[int(index * step)] for index in range(limit)}
        else:
            described_images = set()

    texts: list[str] = []
    for index, file in enumerate(files):
        text = cache.get(file) if cache is not None else None
        if text is None:
            text = extract_text(file, settings)
            may_describe = file.kind is not Kind.IMAGE or index in described_images
            if not text and may_describe:
                text = describe_binary(file, settings)
            if cache is not None and may_describe:
                cache.put(file, text)
        texts.append(text)
    names = _name_phrases(files)
    kinds = [kind_phrase(file.kind) for file in files]
    terms = [file_terms(file.stem, text) for file, text in zip(files, texts, strict=True)]
    return PreparedRecord(files, texts, names, kinds, terms)


def _encode_unique(
    texts: list[str], embedder: Embedder, cache: EvidenceCache | None
) -> np.ndarray:
    """Embed distinct nonblank inputs once, reusing versioned persistent vectors."""
    unique = list(dict.fromkeys(text for text in texts if text.strip()))
    if not unique:
        return embedder.encode(texts)

    model = getattr(embedder, "cache_key", None)
    cached = cache.get_embeddings(model, unique) if cache is not None and model else {}
    missing = [text for text in unique if text not in cached]
    fresh = embedder.encode(missing) if missing else None
    if fresh is not None and cached:
        cached_dim = next(iter(cached.values())).size
        if fresh.shape[1] != cached_dim:
            cached = {}
            missing = unique
            fresh = embedder.encode(missing)
    if fresh is not None and cache is not None and model:
        cache.put_embeddings(model, missing, fresh)

    dimensions = fresh.shape[1] if fresh is not None else next(iter(cached.values())).size
    vectors = np.zeros((len(texts), dimensions), dtype=np.float32)
    by_text = dict(cached)
    if fresh is not None:
        by_text.update(zip(missing, fresh, strict=True))
    for index, text in enumerate(texts):
        if text.strip():
            vectors[index] = by_text[text]
    return vectors


def _compose_record(
    prepared: PreparedRecord,
    text_vectors: np.ndarray,
    name_vectors: np.ndarray,
    kind_vectors: np.ndarray,
    settings: Settings,
) -> VectorRecord:
    files, texts, names, _kinds, terms = prepared
    dimensions = text_vectors.shape[1]
    # Orthogonal blocks prevent cross-source similarity; square-root weights
    # preserve each source's configured cosine share.
    vectors = np.zeros((len(files), dimensions * 3), dtype=np.float32)
    topical = np.zeros(len(files), dtype=bool)

    for index, (entry, text, name) in enumerate(zip(files, texts, names, strict=True)):
        if entry.kind is Kind.JUNK or entry.size == 0:
            continue
        mix = _mix_for(entry, text, name, settings)
        vectors[index, :dimensions] = math.sqrt(mix.text) * text_vectors[index]
        vectors[index, dimensions : 2 * dimensions] = (
            math.sqrt(mix.name) * name_vectors[index]
        )
        vectors[index, 2 * dimensions :] = (
            math.sqrt(mix.kind) * kind_vectors[index]
        )
        topical[index] = bool(text.strip()) or bool(name.strip())

    return VectorRecord(texts, normalise(vectors), topical, terms)


def _vectorize_prepared(
    prepared: list[PreparedRecord],
    *,
    embedder: Embedder,
    settings: Settings,
    cache: EvidenceCache | None,
) -> list[VectorRecord]:
    """Batch content separately from short name and kind phrases."""
    lengths = [len(record.files) for record in prepared]
    all_texts = [text for record in prepared for text in record.texts]
    all_names = [name for record in prepared for name in record.names]
    all_kinds = [kind for record in prepared for kind in record.kinds]
    text_vectors = _encode_unique(all_texts, embedder, cache)
    short_vectors = _encode_unique([*all_names, *all_kinds], embedder, cache)
    name_vectors = short_vectors[: len(all_names)]
    kind_vectors = short_vectors[len(all_names) :]

    records: list[VectorRecord] = []
    offset = 0
    for source, length in zip(prepared, lengths, strict=True):
        end = offset + length
        records.append(
            _compose_record(
                source,
                text_vectors[offset:end],
                name_vectors[offset:end],
                kind_vectors[offset:end],
                settings,
            )
        )
        offset = end
    return records


def vectorize(
    files: list[FileEntry],
    *,
    embedder: Embedder,
    settings: Settings = DEFAULT_SETTINGS,
    cache: EvidenceCache | None = None,
) -> VectorRecord:
    """Turn scanned files into the evidence needed by signals."""
    prepared = _prepare(files, settings=settings, cache=cache)
    return _vectorize_prepared(
        [prepared], embedder=embedder, settings=settings, cache=cache
    )[0]


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
    paths: list[Path] = []
    prepared: list[PreparedRecord] = []
    for done, folder in enumerate(contents, start=1):
        report(Progress("read", done, len(contents), folder.path, len(folder.files)))
        if len(folder.files) < settings.meaningful_cluster_min:
            continue
        paths.append(folder.path.resolve())
        prepared.append(_prepare(folder.files, settings=settings, cache=cache))
    vectorized = _vectorize_prepared(
        prepared, embedder=embedder, settings=settings, cache=cache
    )
    for path, record in zip(paths, vectorized, strict=True):
        records[path] = record
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
