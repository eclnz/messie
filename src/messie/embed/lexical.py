"""Lexical backend — hashed TF-IDF over words and character n-grams.

Always available: nothing but numpy, no model, no download. It has no notion of
synonymy, so it is weaker than the static-embedding backends on short or
differently-worded text, but it separates genuinely different subject matter
perfectly well, and it makes messie work on a machine that has never been
online.

Token hashing uses blake2b rather than ``hash()``, which is salted per process
and would make vectors differ between runs.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter

import numpy as np

from messie.embed import normalise
from messie.tokens import split_words

_DIM = 2048
_NGRAM = 4


def _bucket(token: str, dim: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % dim


def _features(text: str, max_words: int) -> Counter[str]:
    words = split_words(text)[:max_words]
    feats: Counter[str] = Counter(words)
    # Character n-grams rescue short inputs (a three-word filename) and shrug
    # off plurals and small spelling drift.
    for word in words:
        if len(word) >= _NGRAM + 1:
            for i in range(len(word) - _NGRAM + 1):
                feats["#" + word[i : i + _NGRAM]] += 1
    return feats


class LexicalEmbedder:
    name = "lexical"
    #: Hashed TF-IDF is sparse, so even same-topic pairs score low.
    scale = 0.15

    def __init__(self, dim: int = _DIM, max_words: int = 600) -> None:
        self.dim = dim
        self.max_words = max_words

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        per_doc = [_features(t, self.max_words) for t in texts]
        n_docs = len(texts)

        doc_freq: Counter[str] = Counter()
        for feats in per_doc:
            doc_freq.update(feats.keys())

        out = np.zeros((n_docs, self.dim), dtype=np.float32)
        for row, feats in enumerate(per_doc):
            for token, count in feats.items():
                tf = 1.0 + math.log(count)
                idf = math.log((n_docs + 1) / (doc_freq[token] + 1)) + 1.0
                out[row, _bucket(token, self.dim)] += tf * idf
        return normalise(out)
