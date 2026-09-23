#!/usr/bin/env python3
"""Measure what the algorithm actually does, instead of reasoning about it.

Every structural bug in messie so far was found by printing numbers: comparing
normalised centroids inflated similarity and welded unrelated subjects
together; both backend scales were guessed from a four-document probe and were
badly wrong; a CSV saved as .txt read as gibberish because extraction was
discarding line breaks. None of that was visible in the code. All of it was
obvious in a table.

Those measurements used to be throwaway scripts. This is them made permanent,
so the constants in the source have a derivation anyone can re-run:

    python scripts/calibrate.py                 # everything, default backend
    python scripts/calibrate.py --backend sentence
    python scripts/calibrate.py --json          # for machines

Sections:

    separation   how far apart the corpus subjects are, per backend
    sweep        which clustering threshold best separates them, and the
                 backend scale that threshold implies
    realworld    how often real, coherent directories on this machine are
                 wrongly called messy — the only sample nobody authored to
                 suit the tool

``tests/test_calibration.py`` asserts the shipped constants still match what
this reports, so they cannot quietly drift back into magic numbers.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import statistics
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tests"))
sys.path.insert(0, str(_ROOT / "src"))

from corpus import ALL_TOPICS, TOPICS  # noqa: E402
from corpus.build import build_coherent, build_mixed  # noqa: E402

from messie.analyze import Engine  # noqa: E402
from messie.cluster import cluster_vectors  # noqa: E402
from messie.config import DEFAULT_SETTINGS  # noqa: E402
from messie.embed import get_embedder  # noqa: E402
from messie.scan import read_dir  # noqa: E402
from messie.score import Verdict  # noqa: E402

# --- reports ---------------------------------------------------------------


@dataclass
class Separation:
    backend: str
    intra_min: float
    intra_median: float
    inter_median: float
    inter_p95: float
    inter_max: float
    closest_pairs: list[tuple[str, str, float]] = field(default_factory=list)


@dataclass
class SweepPoint:
    threshold: float
    scale: float
    subjects_held: float
    pairs_separated: float

    @property
    def total(self) -> float:
        return self.subjects_held + self.pairs_separated


@dataclass
class RealWorld:
    judged: int
    messy: int
    rate: float
    by_signal: dict[str, int] = field(default_factory=dict)
    offenders: list[tuple[str, list[str]]] = field(default_factory=list)


@dataclass
class Sweep:
    backend: str
    shipped_scale: float
    best: SweepPoint
    points: list[SweepPoint]


# --- measurement -----------------------------------------------------------


def measure_separation(backend: str, top: int = 6) -> Separation:
    """Average-link similarity within each subject, and between every pair."""
    embedder = get_embedder(backend)
    labels, texts = [], []
    for topic, entries in TOPICS.items():
        for stem, text in entries:
            labels.append(topic)
            texts.append(f"{stem} {text}")

    vectors = embedder.encode(texts)
    sim = vectors @ vectors.T
    index = {t: [i for i, lab in enumerate(labels) if lab == t] for t in TOPICS}

    intra = {}
    for topic, rows in index.items():
        block = sim[np.ix_(rows, rows)]
        intra[topic] = float((block.sum() - np.trace(block)) / (len(rows) * (len(rows) - 1)))

    inter = []
    for a, b in itertools.combinations(index, 2):
        inter.append((float(sim[np.ix_(index[a], index[b])].mean()), a, b))
    inter.sort(reverse=True)
    values = [v for v, _, _ in inter]

    return Separation(
        backend=backend,
        intra_min=min(intra.values()),
        intra_median=statistics.median(intra.values()),
        inter_median=statistics.median(values),
        inter_p95=float(np.percentile(values, 95)),
        inter_max=max(values),
        closest_pairs=[(a, b, round(v, 3)) for v, a, b in inter[:top]],
    )


def sweep_threshold(
    backend: str, *, pairs: int = 90, topics: int = 0, seed: int = 4
) -> Sweep:
    """Which clustering threshold best tells the corpus subjects apart.

    Two things are traded off. Too low and every subject stays whole but
    unrelated ones merge; too high and unrelated ones separate but real
    subjects shatter. The sum of the two rates is maximised at the crossover.
    """
    chosen = list(ALL_TOPICS)[:topics] if topics else list(ALL_TOPICS)
    engine = Engine(embedder=get_embedder(backend))
    tmp = Path(tempfile.mkdtemp(prefix="messie-calibrate-"))

    single = {}
    for topic in chosen:
        folder = build_coherent(tmp / "one" / topic, topic, 6)
        single[topic] = engine.vectorize(read_dir(folder).files).vectors

    rng = random.Random(seed)
    combos = list(itertools.combinations(chosen, 2))
    rng.shuffle(combos)
    both = {}
    for a, b in combos[:pairs]:
        folder = build_mixed(tmp / "two" / f"{a}__{b}", {a: 5, b: 5})
        files = read_dir(folder).files
        stems_a = {stem for stem, _ in TOPICS[a]}
        origin = np.array([0 if f.stem in stems_a else 1 for f in files])
        both[(a, b)] = (engine.vectorize(files).vectors, origin)

    points = []
    for threshold in np.arange(0.10, 0.50, 0.01):
        held = sum(1 for v in single.values() if cluster_vectors(v, threshold).n_clusters == 1)
        apart = 0
        for vectors, origin in both.values():
            clustering = cluster_vectors(vectors, threshold)
            merged = any(
                len(set(origin[clustering.members(cid)])) > 1
                for cid in range(clustering.n_clusters)
            )
            apart += not merged
        points.append(
            SweepPoint(
                threshold=round(float(threshold), 3),
                scale=round(float(threshold) / DEFAULT_SETTINGS.cluster_rel, 3),
                subjects_held=round(held / max(1, len(single)), 3),
                pairs_separated=round(apart / max(1, len(both)), 3),
            )
        )

    return Sweep(
        backend=backend,
        shipped_scale=float(getattr(get_embedder(backend), "scale", 0.0)),
        best=max(points, key=lambda p: p.total),
        points=points,
    )


def measure_real_world(limit: int = 90) -> RealWorld:
    """Judge real directories that were not written for this test.

    A package directory is coherent by construction — one project, one purpose
    — so a high rate here means the thresholds fit the fixtures rather than the
    world. This is how ``garbled`` was caught: perfect on synthetic nonsense,
    wrong on every real file it flagged.
    """
    import os
    import sysconfig

    from messie.analyze import analyze_dir

    roots = []
    for key in ("stdlib", "purelib", "platlib"):
        path = sysconfig.get_paths().get(key)
        if path and Path(path).is_dir():
            roots.append(Path(path))
    roots.append(_ROOT)

    folders: list[Path] = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(
                d for d in dirnames if not d.startswith((".", "__pycache__", "test"))
            )
            if len(filenames) >= 8:
                folders.append(Path(dirpath))
            if len(folders) >= limit:
                break
        if len(folders) >= limit:
            break

    judged = messy = 0
    by_signal: dict[str, int] = {}
    offenders: list[tuple[str, list[str]]] = []
    for folder in sorted(set(folders))[:limit]:
        try:
            analysis = analyze_dir(folder)
        except Exception:  # noqa: BLE001
            continue
        if not analysis.judged:
            continue
        judged += 1
        for finding in analysis.findings:
            by_signal[finding.code] = by_signal.get(finding.code, 0) + 1
        if analysis.verdict >= Verdict.MESSY:
            messy += 1
            offenders.append((folder.name, [f.code for f in analysis.findings]))

    return RealWorld(
        judged=judged,
        messy=messy,
        rate=round(messy / judged, 4) if judged else 0.0,
        by_signal=dict(sorted(by_signal.items(), key=lambda kv: -kv[1])),
        offenders=offenders[:8],
    )


# --- printing --------------------------------------------------------------


def _print_separation(report: Separation) -> None:
    print(f"\nSEPARATION · {report.backend}")
    print(f"  within a subject   min {report.intra_min:.3f}   median {report.intra_median:.3f}")
    print(
        f"  between subjects   median {report.inter_median:.3f}   "
        f"p95 {report.inter_p95:.3f}   max {report.inter_max:.3f}"
    )
    print("  closest pairs:")
    for a, b, value in report.closest_pairs:
        print(f"      {value:.3f}  {a} ~ {b}")


def _print_sweep(report: Sweep) -> None:
    print(f"\nTHRESHOLD SWEEP · {report.backend}")
    print(f"  {'thresh':>7} {'scale':>7} {'subjects held':>15} {'pairs apart':>13}")
    shown = {0.14, 0.18, 0.22, 0.26, 0.30, 0.34, 0.38, 0.42}
    for point in report.points:
        if round(point.threshold, 2) in shown:
            print(
                f"  {point.threshold:>7.2f} {point.scale:>7.2f} "
                f"{point.subjects_held:>14.0%} {point.pairs_separated:>13.0%}"
            )
    best = report.best
    print(
        f"  best threshold {best.threshold:.2f} -> scale {best.scale:.2f} "
        f"(subjects {best.subjects_held:.0%}, pairs {best.pairs_separated:.0%})"
    )
    print(f"  shipped scale  {report.shipped_scale:.2f}", end="")
    drift = abs(report.shipped_scale - best.scale)
    print("   ok" if drift <= 0.06 else f"   DRIFTED by {drift:.2f} — update the backend")


def _print_real_world(report: RealWorld) -> None:
    print("\nREAL DIRECTORIES (nobody wrote these for us)")
    print(f"  coherent folders judged     {report.judged}")
    print(f"  called messy or worse       {report.messy}  ({report.rate:.1%})")
    print("  signals firing:")
    for code, count in report.by_signal.items():
        print(f"      {code:<22}{count:>4}  {count / max(1, report.judged):>5.0%}")
    for name, codes in report.offenders:
        print(f"      flagged: {name[:34]:36} {codes}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", default="wordllama")
    parser.add_argument(
        "--sections", default="separation,sweep,realworld",
        help="comma-separated subset to run",
    )
    parser.add_argument("--pairs", type=int, default=90, help="subject pairs in the sweep")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    wanted = {s.strip() for s in args.sections.split(",")}
    out: dict[str, object] = {}

    if "separation" in wanted:
        out["separation"] = measure_separation(args.backend)
    if "sweep" in wanted:
        out["sweep"] = sweep_threshold(args.backend, pairs=args.pairs)
    if "realworld" in wanted:
        out["realworld"] = measure_real_world()

    if args.json:
        print(json.dumps({k: asdict(v) for k, v in out.items()}, indent=2, default=str))
        return 0

    print(f"messie calibration · {len(TOPICS)} subjects, "
          f"{sum(len(v) for v in TOPICS.values())} documents")
    if "separation" in out:
        _print_separation(out["separation"])  # type: ignore[arg-type]
    if "sweep" in out:
        _print_sweep(out["sweep"])  # type: ignore[arg-type]
    if "realworld" in out:
        _print_real_world(out["realworld"])  # type: ignore[arg-type]
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
