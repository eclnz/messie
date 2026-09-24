"""Offline WordLlama embedding backend."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from messie.embed import BackendUnavailable, encode_nonblank

_CONFIG = "l2_supercat"
_TOKENIZER_FILE = f"{_CONFIG}_tokenizer_config.json"


def _seed_tokenizer(wordllama_cls) -> None:
    """Put the wheel's own tokenizer where the loader will find it offline."""
    import wordllama as _pkg

    bundled = Path(_pkg.__file__).parent / "tokenizers" / _TOKENIZER_FILE
    if not bundled.exists():
        return
    try:
        cache_dir = Path(wordllama_cls.get_file_path("tokenizer", None))
    except Exception:  # noqa: BLE001 - upstream layout changed; let load() decide
        return
    target = cache_dir / _TOKENIZER_FILE
    if target.exists():
        return
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundled, target)
    except OSError:
        pass


class WordLlamaEmbedder:
    name = "wordllama"
    #: Calibrated by ``scripts/calibrate.py``.
    scale = 0.40

    def __init__(self, dim: int = 256) -> None:
        try:
            from wordllama import WordLlama
        except ImportError as exc:
            raise BackendUnavailable(
                "wordllama is not installed — it is a hard dependency, so this "
                "means a broken install (pip install --force-reinstall messie)"
            ) from exc

        _seed_tokenizer(WordLlama)
        try:
            self._model = WordLlama.load(dim=dim, disable_download=True)
        except Exception as exc:  # noqa: BLE001 - missing weights, bad cache, layout change
            raise BackendUnavailable(f"wordllama model unavailable offline: {exc}") from exc

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 256), dtype=np.float32)
        return encode_nonblank(texts, lambda batch: self._model.embed(batch, norm=True), 256)
