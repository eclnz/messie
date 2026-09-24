"""Turning file text into vectors, locally.

There is one backend. wordllama is a hard dependency rather than one option
among several, so a backend always exists and it never needs the network — its
weights and tokenizer ship inside the wheel.

Three others have been tried and measured away, which is worth recording so
they are not reinvented:

    lexical     hashed TF-IDF, for machines that could not fetch a model. Held
                71% of subjects together against wordllama's 97% — an older,
                smaller corpus than the figures below, so compare it only with
                the 97%, not with them. Since wordllama downloads nothing, a
                fallback for machines that cannot download bought nothing.
    model2vec   significantly worse on the example corpus (sum of held and
                separated rates 1.605 against 1.649, bootstrap P=99.6%), in
                exchange for a speed gain nobody can perceive on a stage that
                takes 25ms.
    sentence    sentence-transformers. Statistically indistinguishable at its
                own best threshold (1.611 against 1.649, 95% CI spanning
                zero), but decisively worse where messie actually operates:
                asked to keep 90% of unrelated subject pairs apart, it holds
                59% of real subjects together against wordllama's 73%. It also
                costs 30x the runtime, ~400MB of torch, and a download on
                first use — and its optimal scale moved 0.34/0.37/0.43 across
                three reshuffles of one corpus, a spread wider than the drift
                tolerance the calibration guard allows, so no stable constant
                could be shipped for it at all.

``scripts/calibrate.py`` produced those numbers and can reproduce them against
any new candidate. The Embedder protocol below is the whole contract: a name, a
scale, and ``encode``. Adding a fourth backend means implementing it, measuring
it, and beating 1.649 at the strict end of the frontier.
"""

from __future__ import annotations

from functools import cache
from typing import Protocol, runtime_checkable

import numpy as np

#: Every backend there is. Still a tuple, and still the thing ``--backend``
#: and ``--doctor`` enumerate, so a second entry costs nothing to reintroduce.
BACKEND_ORDER: tuple[str, ...] = ("wordllama",)


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
