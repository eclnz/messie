"""Naming a cluster.

No language model is involved, so messie does not write prose summaries it
cannot stand behind. Instead each cluster is labelled with the words that are
common inside it and rare in the rest of the folder — class-based TF-IDF. The
output is presented as keywords, which is what it is.

When a cluster has no distinctive vocabulary at all (forty photos called
IMG_4412.HEIC), it says so rather than inventing a theme.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np

from messie.tokens import content_tokens, name_tokens

NO_LABEL = "no shared wording"

#: A term has to show up in at least this share of a cluster to name it.
_MIN_SUPPORT = 0.30
_MIN_SCORE = 0.15


def file_terms(stem: str, text: str, *, content_limit: int = 200) -> Counter[str]:
    """Terms describing one file. Filename words count double — they are the
    words a person actually chose."""
    terms: Counter[str] = Counter()
    for token in name_tokens(stem):
        terms[token] += 2
    for token in content_tokens(text, limit=content_limit):
        terms[token] += 1
    return terms


def label_clusters(
    labels: np.ndarray,
    terms_per_file: list[Counter[str]],
    n_clusters: int,
    top_n: int = 3,
) -> dict[int, list[str]]:
    """Distinctive keywords for each cluster, best first."""
    if n_clusters == 0:
        return {}

    cluster_terms: list[Counter[str]] = [Counter() for _ in range(n_clusters)]
    cluster_docs: list[int] = [0] * n_clusters
    support: list[Counter[str]] = [Counter() for _ in range(n_clusters)]

    for idx, cid in enumerate(labels):
        if cid < 0:
            continue
        cluster_terms[cid].update(terms_per_file[idx])
        support[cid].update(set(terms_per_file[idx]))
        cluster_docs[cid] += 1

    # How many clusters each term shows up in: a term in every cluster
    # distinguishes nothing.
    spread: Counter[str] = Counter()
    for counts in cluster_terms:
        spread.update(set(counts))

    out: dict[int, list[str]] = {}
    for cid in range(n_clusters):
        total = sum(cluster_terms[cid].values()) or 1
        docs = cluster_docs[cid] or 1
        scored: list[tuple[float, str]] = []
        for term, count in cluster_terms[cid].items():
            if support[cid][term] / docs < _MIN_SUPPORT:
                continue
            tf = count / total
            idf = math.log(n_clusters / spread[term]) + 1.0 if spread[term] else 1.0
            score = tf * idf * math.sqrt(len(term))
            if score >= _MIN_SCORE * 0.01:
                scored.append((score, term))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        out[cid] = [term for _, term in scored[:top_n]] or [NO_LABEL]
    return out


def format_label(terms: list[str]) -> str:
    if not terms or terms == [NO_LABEL]:
        return NO_LABEL
    return " · ".join(terms)
