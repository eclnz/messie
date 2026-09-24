"""Local text embedding backends."""

from __future__ import annotations

from functools import cache
from typing import Protocol, runtime_checkable

import numpy as np

BACKEND_ORDER: tuple[str, ...] = ("wordllama",)


@runtime_checkable
class Embedder(Protocol):
    name: str
    #: Typical within-subject cosine similarity.
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


def encodable(text: str) -> str:
    """Replace invalid Unicode before passing text to a tokenizer."""
    return text.encode("utf-8", "replace").decode("utf-8")


def encode_nonblank(texts: list[str], encode_fn, dim: int) -> np.ndarray:
    """Encode non-blank texts and use zero rows for blanks."""
    out = np.zeros((len(texts), dim), dtype=np.float32)
    wanted = [i for i, t in enumerate(texts) if t.strip()]
    if wanted:
        encoded = np.asarray(encode_fn([encodable(texts[i]) for i in wanted]), dtype=np.float32)
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
    raise BackendUnavailable(f"unknown backend {name!r}")


def get_embedder(preference: str | None = None) -> Embedder:
    """Return the requested backend, or the default backend."""
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
