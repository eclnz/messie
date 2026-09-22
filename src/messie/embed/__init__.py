"""Turning file text into vectors, locally.

Backends are tried best-first, and every one of them runs on this machine.

    wordllama   static embeddings, weights ship inside the wheel — no download
    model2vec   static embeddings, fetches a model once on first use
    sentence    sentence-transformers, best quality, heaviest

wordllama is a hard dependency rather than one option among several, so there
is always a backend and it never needs the network. There was once a hashed
TF-IDF fallback for machines that could not fetch a model; measured against the
example corpus it held only about 71% of subjects together against wordllama's
97%, and since wordllama downloads nothing the fallback bought nothing. A
second-rate verdict is worse than an honest dependency.
"""

from __future__ import annotations

from functools import cache
from typing import Protocol, runtime_checkable

import numpy as np

#: Preference order for automatic selection.
BACKEND_ORDER: tuple[str, ...] = ("wordllama", "model2vec", "sentence")


@runtime_checkable
class Embedder(Protocol):
    name: str
    #: Typical cosine between two files on the same subject under this
    #: backend. Thresholds are expressed as fractions of it.
    scale: float

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return one L2-normalised row per input text."""
        ...


class BackendUnavailable(RuntimeError):
    """Raised when a backend's dependencies or model are not present."""


def normalise(vectors: np.ndarray) -> np.ndarray:
    """Scale rows to unit length, leaving all-zero rows alone."""
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1.0, norms)


def encode_nonblank(texts: list[str], encode_fn, dim: int) -> np.ndarray:
    """Run ``encode_fn`` over the non-blank texts, leaving blanks as zero rows.

    A blank string has no meaning to represent. Passing one to a model yields a
    zero-norm vector and a divide-by-zero warning, and whatever comes out the
    other side would be noise pretending to be a topic.
    """
    out = np.zeros((len(texts), dim), dtype=np.float32)
    wanted = [i for i, t in enumerate(texts) if t.strip()]
    if wanted:
        encoded = np.asarray(encode_fn([texts[i] for i in wanted]), dtype=np.float32)
        if encoded.shape[1] != dim:  # backend reported a different width
            out = np.zeros((len(texts), encoded.shape[1]), dtype=np.float32)
        out[wanted] = np.nan_to_num(encoded, nan=0.0, posinf=0.0, neginf=0.0)
    return normalise(out)


@cache
def _load(name: str) -> Embedder:
    """Load a backend, once. Inference is stateless, so sharing is safe."""
    if name == "wordllama":
        from messie.embed.wordllama_backend import WordLlamaEmbedder

        return WordLlamaEmbedder()
    if name == "model2vec":
        from messie.embed.model2vec_backend import Model2VecEmbedder

        return Model2VecEmbedder()
    if name == "sentence":
        from messie.embed.sentence_backend import SentenceEmbedder

        return SentenceEmbedder()
    raise BackendUnavailable(f"unknown backend {name!r}")


def get_embedder(preference: str | None = None) -> Embedder:
    """Best available backend, or the named one.

    Naming a backend explicitly makes its absence an error rather than a silent
    downgrade — a verdict should never quietly come from a weaker model than
    the one that was asked for.
    """
    if preference and preference != "auto":
        return _load(preference)

    errors: list[str] = []
    for name in BACKEND_ORDER:
        try:
            return _load(name)
        except Exception as exc:  # noqa: BLE001 - try the next backend
            errors.append(f"{name}: {exc}")
    raise BackendUnavailable("no embedding backend available: " + "; ".join(errors))


def backend_status() -> list[tuple[str, bool, str]]:
    """(name, available, detail) for every backend — powers ``messie doctor``."""
    out = []
    for name in BACKEND_ORDER:
        try:
            embedder = _load(name)
            probe = embedder.encode(["a short probe sentence"])
            out.append((name, True, f"ready, {probe.shape[1]} dims"))
        except Exception as exc:  # noqa: BLE001
            out.append((name, False, str(exc).split("\n")[0][:120]))
    return out
