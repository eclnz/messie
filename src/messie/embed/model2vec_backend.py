"""Model2Vec backend — optional, fetches a small model once on first use."""

from __future__ import annotations

import numpy as np

from messie.embed import BackendUnavailable, encode_nonblank

_DEFAULT_MODEL = "minishlab/potion-base-8M"


class Model2VecEmbedder:
    name = "model2vec"
    scale = 0.45

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        try:
            from model2vec import StaticModel
        except ImportError as exc:
            raise BackendUnavailable(
                "model2vec is not installed (pip install messie[model2vec])"
            ) from exc
        try:
            self._model = StaticModel.from_pretrained(model_name)
        except Exception as exc:  # noqa: BLE001 - offline, or model not cached
            raise BackendUnavailable(f"model2vec model {model_name!r} unavailable: {exc}") from exc

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 256), dtype=np.float32)
        return encode_nonblank(texts, lambda batch: self._model.encode(batch), 256)
