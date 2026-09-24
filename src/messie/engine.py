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
from messie.kinds import Kind, is_textual, kind_phrase
from messie.label import file_terms, label_clusters
from messie.metadata import describe
from messie.result import DirAnalysis, SignalContext, SkipReason, VectorRecord
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
_MIX_META = Mix(0.85, 0.15, 0.00)

#: measurements. "4032x3024" names no subject; "scanned paper document"
_WORDS_RE = re.compile(r"[^\W\d_]{3,}")

#: A filename word shared by at least this share of the folder is a naming
#: convention, not a subject.
_COMMON_NAME_SHARE = 0.7

def _name_phrases(files: list[FileEntry]) -> list[str]:
    "Filenames as phrases, with folder-wide boilerplate removed."
    token_lists = [name_tokens(f.stem) for f in files]
    common: set[str] = set()
    if len(files) >= 5:
        frequency: Counter[str] = Counter()
        for tokens in token_lists:
            frequency.update(set(tokens))
        cutoff = _COMMON_NAME_SHARE * len(files)
        common = {token for token, count in frequency.items() if count >= cutoff}
    return [" ".join(t for t in tokens if t not in common) for tokens in token_lists]

def _text_for(entry: FileEntry, settings: Settings) -> str:
    return extract_text(entry, settings) or describe(entry)


def _mix_for(entry: FileEntry, text: str, name: str, settings: Settings) -> Mix:
    """Which blend this file has earned."""
    has_text = bool(text.strip())
    has_name = bool(name.strip())

    if has_text and not is_textual(entry.kind) and _WORDS_RE.search(text):
        return _MIX_META
    if has_text and len(text) >= settings.min_text_chars:
        return _MIX_RICH
    if has_text:
        return _MIX_THIN
    if has_name:
        return _MIX_NAME
    return _MIX_KIND


def vectorize(
    files: list[FileEntry],
    *,
    embedder: Embedder,
    settings: Settings = DEFAULT_SETTINGS,
) -> VectorRecord:
    """Texts, unit vectors, the topical mask, and per-file terms."""
    texts = [_text_for(file, settings) for file in files]
    names = _name_phrases(files)
    kinds = [kind_phrase(file.kind) for file in files]

    text_vecs = embedder.encode(texts)
    name_vecs = embedder.encode(names)
    kind_vecs = embedder.encode(kinds)

    out = np.zeros((len(files), text_vecs.shape[1]), dtype=np.float32)
    topical = np.zeros(len(files), dtype=bool)

    for i, (entry, text, name) in enumerate(zip(files, texts, names, strict=True)):
        if entry.kind is Kind.JUNK or entry.size == 0:
            continue
        mix = _mix_for(entry, text, name, settings)
        out[i] = mix.text * text_vecs[i] + mix.name * name_vecs[i] + mix.kind * kind_vecs[i]
        topical[i] = bool(text.strip()) or bool(name.strip())

    terms = [file_terms(file.stem, text) for file, text in zip(files, texts, strict=True)]
    return VectorRecord(texts, normalise(out), topical, terms)


def profile_of(vectors: np.ndarray) -> np.ndarray:
    """A folder's contents as one vector."""
    if vectors.size == 0:
        return np.zeros(0, dtype=np.float32)
    return vectors.mean(axis=0).astype(np.float32)


def profile(
    files: list[FileEntry],
    *,
    embedder: Embedder,
    settings: Settings = DEFAULT_SETTINGS,
) -> np.ndarray:
    if not files:
        return np.zeros(0, dtype=np.float32)
    return profile_of(vectorize(files, embedder=embedder, settings=settings).vectors)


def analyze(
    contents: DirContents,
    *,
    embedder: Embedder | None = None,
    settings: Settings = DEFAULT_SETTINGS,
    child_profiles: dict[Path, np.ndarray] | None = None,
    precomputed: VectorRecord | None = None,
) -> DirAnalysis:
    """Judge one folder, reusing ``precomputed`` vectors when supplied."""
    embedder = embedder or get_embedder()
    thresholds = Thresholds.derive(
        embedder.scale, settings, settings.cluster_threshold_override
    )
    if len(contents.files) < settings.min_files_to_judge:
        return DirAnalysis(
            path=contents.path,
            backend=embedder.name,
            n_files=len(contents.files),
            truncated=contents.truncated,
            judged=False,
            skip_reason=SkipReason.TOO_FEW_FILES,
        )

    record = precomputed or vectorize(contents.files, embedder=embedder, settings=settings)
    clustering = cluster_vectors(record.vectors, thresholds.cluster)
    context = SignalContext(
        path=contents.path,
        settings=settings,
        thresholds=thresholds,
        backend=embedder.name,
        files=list(contents.files),
        texts=record.texts,
        vectors=record.vectors,
        topical=record.topical,
        terms=record.terms,
        clustering=clustering,
        cluster_labels=label_clusters(
            clustering.labels, record.terms, clustering.n_clusters
        ),
        subdirs=list(contents.subdirs),
        truncated=contents.truncated,
        child_profiles=child_profiles or {},
    )
    signal_run = run_all(context)
    score, verdict = score_findings(signal_run.findings, settings)
    return DirAnalysis(
        path=contents.path,
        backend=embedder.name,
        n_files=context.n_files,
        truncated=contents.truncated,
        clusters=clustering.n_clusters,
        meaningful_clusters=len(context.meaningful_clusters()),
        findings=signal_run.findings,
        failed_signals=signal_run.failed,
        score=score,
        verdict=verdict,
    )
