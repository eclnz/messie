"""The default embedder and shared embedding helpers."""

from __future__ import annotations

from functools import cache
from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Embedder(Protocol):
    name: str
    #: Typical within-subject cosine similarity.
    scale: float

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return one L2-normalised row per input text."""
        ...


class EmbedderUnavailable(RuntimeError):
    """Raised when the default embedder cannot be loaded."""


def normalise(vectors: np.ndarray) -> np.ndarray:
    """Scale rows to unit length, leaving all-zero rows alone."""
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1.0, norms)


def encodable(text: str) -> str:
    """Replace invalid Unicode before passing text to a tokenizer."""
    return text.encode("utf-8", "replace").decode("utf-8")


def encode_nonblank(texts: list[str], encode_fn, dim: int) -> np.ndarray:
    """Encode non-blank texts and use zero rows for blanks."""
    out = np.zeros((len(texts), dim), dtype=np.float32)
    wanted = [i for i, t in enumerate(texts) if t.strip()]
    if wanted:
        encoded = np.asarray(encode_fn([encodable(texts[i]) for i in wanted]), dtype=np.float32)
        if encoded.shape[1] != dim:
            out = np.zeros((len(texts), encoded.shape[1]), dtype=np.float32)
        out[wanted] = np.nan_to_num(encoded, nan=0.0, posinf=0.0, neginf=0.0)
    return normalise(out)


@cache
def get_embedder() -> Embedder:
    """Load the embedder used when a caller does not supply one."""
    from messie.embed.wordllama import WordLlamaEmbedder

    return WordLlamaEmbedder()
