"""Putting it together: read a folder, work out what is in it, judge it.

A file's vector blends three things, in descending order of trust:

  what it says   the text actually inside it
  what it is called  the words in its filename
  what it is     a stand-in phrase for its kind

A photo named ``IMG_4412.HEIC`` has only the third, so it lands with the other
photos rather than looking like a stray. Files in that position are marked
untopical and excluded from signals that would otherwise punish them for being
unreadable.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import numpy as np

from messie.cache import Cache
from messie.cluster import Clustering, cluster_vectors
from messie.config import DEFAULT_SETTINGS, Settings, Thresholds
from messie.embed import Embedder, get_embedder, normalise
from messie.extract import extract_text
from messie.kinds import kind_phrase
from messie.label import file_terms, format_label, label_clusters
from messie.scan import DirContents, FileEntry, read_dir, walk
from messie.score import Verdict, score_findings
from messie.signals import Finding, failed_signals, run_all
from messie.tokens import name_tokens

# How much the text / name / kind vectors count, by how much we could read.
_MIX_RICH = (0.75, 0.20, 0.05)
_MIX_THIN = (0.45, 0.40, 0.15)
_MIX_NAME = (0.00, 0.80, 0.20)
_MIX_KIND = (0.00, 0.00, 1.00)

class VectorRecord(NamedTuple):
    """What vectorize() hands back for one folder."""

    texts: list[str]
    vectors: np.ndarray
    topical: np.ndarray
    terms: list[Counter]


@dataclass
class DirAnalysis:
    """Everything known about one folder, plus the verdict."""

    path: Path
    settings: Settings
    thresholds: Thresholds
    backend: str
    files: list[FileEntry] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    terms: list[Counter] = field(default_factory=list)
    vectors: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), np.float32))
    topical: np.ndarray = field(default_factory=lambda: np.zeros(0, bool))
    clustering: Clustering | None = None
    cluster_labels: dict[int, list[str]] = field(default_factory=dict)
    child_profiles: dict[Path, np.ndarray] = field(default_factory=dict)
    subdirs: list[Path] = field(default_factory=list)
    truncated: int = 0
    judged: bool = True
    skip_reason: str = ""
    findings: list[Finding] = field(default_factory=list)
    #: Signals that raised while judging this folder. A crashed signal and a
    #: quiet one look identical from the outside, so this is carried out to the
    #: report rather than left in a module-level global.
    failed_signals: list[str] = field(default_factory=list)
    score: float = 0.0
    verdict: Verdict = Verdict.TIDY

    # --- conveniences used by the signals ----------------------------------

    @property
    def n_files(self) -> int:
        return len(self.files)

    def meaningful_clusters(self) -> list[int]:
        """Clusters big enough for their presence to mean something."""
        if not self.clustering or self.n_files == 0:
            return []
        floor = max(
            self.settings.meaningful_cluster_min,
            int(self.settings.meaningful_cluster_frac * self.n_files),
        )
        sizes = self.clustering.sizes()
        return [cid for cid, size in sizes.items() if size >= floor]

    def members(self, cid: int) -> list[int]:
        if not self.clustering:
            return []
        return self.clustering.members(cid).tolist()

    def label_of(self, cid: int) -> str:
        return format_label(self.cluster_labels.get(cid, []))

    def names(self, indices: list[int], limit: int = 3) -> list[str]:
        return [self.files[i].name for i in indices[:limit]]

    def mtime_span(self, indices: list[int]) -> tuple[float, float]:
        if not indices:
            return (0.0, 0.0)
        times = [self.files[i].mtime for i in indices]
        return (min(times), max(times))


class Engine:
    """Holds the embedder and cache so a whole tree is analysed with one of each."""

    def __init__(
        self,
        settings: Settings = DEFAULT_SETTINGS,
        embedder: Embedder | None = None,
        cache: Cache | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or get_embedder()
        self.thresholds = Thresholds.derive(
            getattr(self.embedder, "scale", 0.3),
            settings,
            settings.cluster_threshold_override,
        )
        # The cache holds extracted text, which is the expensive part: reading
        # and decompressing files off disk. Vectors are not cached; embedding is
        # cheap next to the disk read.
        self.cache = cache if cache is not None else Cache(enabled=False)

    # --- text ---------------------------------------------------------------

    def _text_for(self, entry: FileEntry) -> str:
        key = Cache.key("text", entry.path, entry.size, entry.mtime)
        hit = self.cache.get(key)
        if hit is not None:
            return hit[1]
        text = extract_text(entry, self.settings)
        self.cache.put(key, np.zeros(1, np.float32), text)
        return text

    # --- vectors ------------------------------------------------------------

    #: A filename word shared by at least this share of the folder is a naming
    #: convention, not a subject.
    _COMMON_NAME_SHARE = 0.7

    def _name_phrases(self, files: list[FileEntry]) -> list[str]:
        """Filenames as phrases, with folder-wide boilerplate removed.

        People prefix filenames with project names, initials and dates. A word
        in nearly every name here says nothing about which files belong with
        which, and leaving it in raises every pairwise similarity at once —
        enough to weld genuinely separate subjects into one group.
        """
        token_lists = [name_tokens(f.stem) for f in files]
        common: set[str] = set()
        if len(files) >= 5:
            frequency: Counter[str] = Counter()
            for tokens in token_lists:
                frequency.update(set(tokens))
            cutoff = self._COMMON_NAME_SHARE * len(files)
            common = {token for token, count in frequency.items() if count >= cutoff}
        return [" ".join(t for t in tokens if t not in common) for tokens in token_lists]

    def vectorize(
        self, files: list[FileEntry]
    ) -> VectorRecord:
        """Return (texts, unit vectors, topical mask, per-file terms)."""
        texts = [self._text_for(f) for f in files]
        names = self._name_phrases(files)
        kinds = [kind_phrase(f.kind) for f in files]

        text_vecs = self.embedder.encode(texts)
        name_vecs = self.embedder.encode(names)
        kind_vecs = self.embedder.encode(kinds)

        dim = text_vecs.shape[1]
        out = np.zeros((len(files), dim), dtype=np.float32)
        topical = np.zeros(len(files), dtype=bool)

        for i, (text, name) in enumerate(zip(texts, names, strict=True)):
            entry = files[i]
            if entry.kind == "junk" or entry.size == 0:
                # Debris has no subject. Leaving it at zero keeps it out of every
                # topic group, so a folder's themes are not padded with leftovers.
                continue

            has_text = bool(text.strip())
            rich = len(text) >= self.settings.min_text_chars
            has_name = bool(name.strip())

            if has_text and rich:
                mix = _MIX_RICH
            elif has_text:
                mix = _MIX_THIN
            elif has_name:
                mix = _MIX_NAME
            else:
                mix = _MIX_KIND

            out[i] = mix[0] * text_vecs[i] + mix[1] * name_vecs[i] + mix[2] * kind_vecs[i]
            topical[i] = has_text or has_name

        terms = [file_terms(f.stem, t) for f, t in zip(files, texts, strict=True)]
        return VectorRecord(texts, normalise(out), topical, terms)

    @staticmethod
    def profile_of(vectors: np.ndarray) -> np.ndarray:
        """A folder's contents as one vector.

        This is the *mean* member vector, not a normalised centroid, so that
        dotting a file against it gives that file's average similarity to the
        folder — the same scale every other threshold is measured on.
        """
        if vectors.size == 0:
            return np.zeros(0, dtype=np.float32)
        return vectors.mean(axis=0).astype(np.float32)

    def profile(self, files: list[FileEntry]) -> np.ndarray:
        if not files:
            return np.zeros(0, dtype=np.float32)
        return self.profile_of(self.vectorize(files)[1])

    # --- analysis -----------------------------------------------------------

    def analyze(
        self,
        contents: DirContents,
        child_profiles: dict[Path, np.ndarray] | None = None,
        precomputed: VectorRecord | None = None,
    ) -> DirAnalysis:
        """Judge one folder. ``precomputed`` reuses vectors built earlier, so a
        tree walk does not embed every folder twice."""
        analysis = DirAnalysis(
            path=contents.path,
            settings=self.settings,
            thresholds=self.thresholds,
            backend=self.embedder.name,
            files=list(contents.files),
            subdirs=list(contents.subdirs),
            truncated=contents.truncated,
            child_profiles=child_profiles or {},
        )

        if len(contents.files) < self.settings.min_files_to_judge:
            analysis.judged = False
            analysis.skip_reason = (
                f"only {len(contents.files)} files — too few to call it anything"
            )
            return analysis

        record = precomputed or self.vectorize(contents.files)
        texts, vectors, topical, terms = record
        analysis.texts = texts
        analysis.vectors = vectors
        analysis.topical = topical
        analysis.terms = terms
        analysis.clustering = cluster_vectors(vectors, self.thresholds.cluster)
        analysis.cluster_labels = label_clusters(
            analysis.clustering.labels, terms, analysis.clustering.n_clusters
        )

        analysis.findings = run_all(analysis)
        analysis.failed_signals = list(failed_signals)
        analysis.score, analysis.verdict = score_findings(analysis.findings, self.settings)
        return analysis


def analyze_dir(
    path: Path | str,
    settings: Settings = DEFAULT_SETTINGS,
    embedder: Embedder | None = None,
    cache: Cache | None = None,
) -> DirAnalysis:
    """Judge a single folder, ignoring what is in its subfolders.

    Folders below it are still read, but only to build a profile of each, so
    that loose files here can be recognised as resembling one of them.
    """
    engine = Engine(settings, embedder, cache)
    root = Path(path).expanduser().resolve()
    contents = read_dir(root, settings)

    profiles = {}
    for sub_contents in walk(root, settings):
        if sub_contents.path.resolve() == root:
            continue
        if len(sub_contents.files) >= settings.meaningful_cluster_min:
            profiles[sub_contents.path.resolve()] = engine.profile(sub_contents.files)
    return engine.analyze(contents, profiles)


def analyze_tree(
    root: Path | str,
    settings: Settings = DEFAULT_SETTINGS,
    embedder: Embedder | None = None,
    cache: Cache | None = None,
) -> list[DirAnalysis]:
    """Judge every folder at or under ``root``, worst first."""
    engine = Engine(settings, embedder, cache)
    all_contents = walk(Path(root), settings)
    by_path = {c.path.resolve(): c for c in all_contents}

    # Vectorise each folder once. The result serves both that folder's own
    # analysis and its parent's view of it as a subfolder.
    records: dict[Path, VectorRecord] = {}
    profiles: dict[Path, np.ndarray] = {}
    for contents in all_contents:
        if len(contents.files) < settings.meaningful_cluster_min:
            continue
        key = contents.path.resolve()
        records[key] = engine.vectorize(contents.files)
        profiles[key] = engine.profile_of(records[key][1])

    results: list[DirAnalysis] = []
    for contents in all_contents:
        key = contents.path.resolve()
        # Every folder underneath, not just the immediate children. People file
        # things away several levels down — ./Archive/2023/Taxes — and loose
        # paperwork upstairs resembles that folder just as much for being deep.
        child_profiles = {
            other: profile
            for other, profile in profiles.items()
            if other != key and other.is_relative_to(key) and other in by_path
        }
        results.append(engine.analyze(contents, child_profiles, records.get(key)))

    engine.cache.commit()
    results.sort(key=lambda a: (-a.score, str(a.path)))
    return results
