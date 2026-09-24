"""Turning a folder's files into vectors, and judging the folder from them.

A file's vector blends three things, in descending order of trust:

  what it says   the text inside it, or what its container says about it
  what it is called  the words in its filename
  what it is     a stand-in phrase for its kind

The third exists only for files with nothing else to offer. A photograph named
``IMG_4412.HEIC`` with its EXIF stripped has only that, so it lands with the
other photographs rather than looking like a stray; a photograph that still
carries its EXIF says what it is in words and does not need telling.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple

import numpy as np

from messie.cluster import cluster_vectors
from messie.config import DEFAULT_SETTINGS, Settings, Thresholds
from messie.embed import Embedder, get_embedder, normalise
from messie.extract import extract_text
from messie.kinds import is_textual, kind_phrase
from messie.label import file_terms, label_clusters
from messie.metadata import describe
from messie.result import DirAnalysis, VectorRecord
from messie.scan import DirContents, FileEntry
from messie.score import score_findings
from messie.signals import run_all
from messie.tokens import name_tokens


class Mix(NamedTuple):
    """How much the text, name and kind vectors each count."""

    text: float
    name: float
    kind: float


# By how much of the file we could actually read.
_MIX_RICH = Mix(0.75, 0.20, 0.05)
_MIX_THIN = Mix(0.45, 0.40, 0.15)
_MIX_NAME = Mix(0.00, 0.80, 0.20)
_MIX_KIND = Mix(0.00, 0.00, 1.00)

# A binary described by its own metadata is short but factual, so it is trusted
# like rich text rather than like a thin scrap of prose, and the kind phrase is
# dropped outright. It has become redundant: "photograph taken with a camera
# Canon EOS R6" already says what the file is, and adding "photograph picture
# image snapshot" on top only restates the one thing every image in the folder
# has in common. That shared restatement is not free. A folder of scans,
# photographs and screenshots sits 0.138 apart on its text alone; carrying the
# kind phrase at the usual weight dragged it to 0.254, and even a residual 0.05
# held it at 0.226 — both the wrong side of the 0.220 line at which two groups
# stop reading as unrelated. At zero it lands at 0.200 and the folder is
# reported, while a single camera roll stays one group, as it should.
_MIX_META = Mix(0.85, 0.15, 0.00)

#: An alphabetic run this long makes a description *words* rather than
#: measurements. "4032x3024" names no subject; "scanned paper document"
#: does, and only the second is worth trusting over everything else.
_WORDS_RE = re.compile(r"[^\W\d_]{3,}")


class Engine:
    """Holds the embedder and derived thresholds for one analysis."""

    def __init__(
        self,
        settings: Settings = DEFAULT_SETTINGS,
        embedder: Embedder | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or get_embedder()
        self.thresholds = Thresholds.derive(
            self.embedder.scale,
            settings,
            settings.cluster_threshold_override,
        )
    # --- text ---------------------------------------------------------------

    def _text_for(self, entry: FileEntry) -> str:
        """What this file says, however it says it.

        Prose comes from ``extract_text``. Anything without prose in it — a
        photograph, an archive, a font — is asked what its container says about
        it instead. Keeping the fallback here rather than inside ``extract_text``
        leaves each of those doing one thing.
        """
        return extract_text(entry, self.settings) or describe(entry)

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

    def _mix_for(self, entry: FileEntry, text: str, name: str) -> Mix:
        """Which blend this file has earned."""
        has_text = bool(text.strip())
        has_name = bool(name.strip())

        # Anything not made of prose was described by its own container rather
        # than read: a font's name table, an archive's members, a photograph's
        # EXIF. Only count that as metadata if it says something in *words* —
        # otherwise a folder where some images carry dimensions and others do
        # not would split into "has numbers" and "has none", which is no kind
        # of subject.
        if has_text and not is_textual(entry.kind) and _WORDS_RE.search(text):
            return _MIX_META
        if has_text and len(text) >= self.settings.min_text_chars:
            return _MIX_RICH
        if has_text:
            return _MIX_THIN
        if has_name:
            return _MIX_NAME
        return _MIX_KIND

    def vectorize(self, files: list[FileEntry]) -> VectorRecord:
        """Texts, unit vectors, the topical mask, and per-file terms."""
        texts = [self._text_for(f) for f in files]
        names = self._name_phrases(files)
        kinds = [kind_phrase(f.kind) for f in files]

        text_vecs = self.embedder.encode(texts)
        name_vecs = self.embedder.encode(names)
        kind_vecs = self.embedder.encode(kinds)

        out = np.zeros((len(files), text_vecs.shape[1]), dtype=np.float32)
        topical = np.zeros(len(files), dtype=bool)

        for i, (entry, text, name) in enumerate(zip(files, texts, names, strict=True)):
            if entry.kind == "junk" or entry.size == 0:
                # Debris has no subject. Leaving it at zero keeps it out of every
                # topic group, so a folder's themes are not padded with leftovers.
                continue
            mix = self._mix_for(entry, text, name)
            out[i] = mix.text * text_vecs[i] + mix.name * name_vecs[i] + mix.kind * kind_vecs[i]
            topical[i] = bool(text.strip()) or bool(name.strip())

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
        return self.profile_of(self.vectorize(files).vectors)

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
        analysis.texts, analysis.vectors, analysis.topical, analysis.terms = record
        analysis.clustering = cluster_vectors(record.vectors, self.thresholds.cluster)
        analysis.cluster_labels = label_clusters(
            analysis.clustering.labels, record.terms, analysis.clustering.n_clusters
        )

        analysis.findings, analysis.failed_signals = run_all(analysis)
        analysis.score, analysis.verdict = score_findings(analysis.findings, self.settings)
        return analysis
