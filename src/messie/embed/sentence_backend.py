"""sentence-transformers backend — optional, heaviest, best quality."""

from __future__ import annotations

import numpy as np

from messie.embed import BackendUnavailable, encode_nonblank

_DEFAULT_MODEL = "all-MiniLM-L6-v2"


class SentenceEmbedder:
    name = "sentence"
    scale = 0.45

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise BackendUnavailable(
                "sentence-transformers is not installed (pip install messie[st])"
            ) from exc
        try:
            self._model = SentenceTransformer(model_name)
        except Exception as exc:  # noqa: BLE001 - offline, or model not cached
            raise BackendUnavailable(f"sentence-transformers model unavailable: {exc}") from exc

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        return encode_nonblank(
            texts,
            lambda batch: self._model.encode(
                batch, show_progress_bar=False, convert_to_numpy=True
            ),
            384,
        )
