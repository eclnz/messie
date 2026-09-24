"""WordLlama, the embedder messie uses by default."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from messie.embed import EmbedderUnavailable, encode_nonblank

_CONFIG = "l2_supercat"
_TOKENIZER_FILE = f"{_CONFIG}_tokenizer_config.json"


def _seed_tokenizer(wordllama_cls) -> None:
    """Put the wheel's tokenizer where WordLlama finds it offline."""
    import wordllama as package

    bundled = Path(package.__file__).parent / "tokenizers" / _TOKENIZER_FILE
    if not bundled.exists():
        return
    try:
        target = Path(wordllama_cls.get_file_path("tokenizer", None)) / _TOKENIZER_FILE
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled, target)
    except OSError:
        return


class WordLlamaEmbedder:
    name = "wordllama"
    scale = 0.40

    def __init__(self, dim: int = 256) -> None:
        try:
            from wordllama import WordLlama
        except ImportError as exc:
            raise EmbedderUnavailable("wordllama is not installed") from exc

        _seed_tokenizer(WordLlama)
        try:
            self._model = WordLlama.load(dim=dim, disable_download=True)
        except Exception as exc:  # noqa: BLE001
            raise EmbedderUnavailable(f"wordllama is unavailable: {exc}") from exc

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 256), dtype=np.float32)
        return encode_nonblank(texts, lambda batch: self._model.embed(batch, norm=True), 256)
