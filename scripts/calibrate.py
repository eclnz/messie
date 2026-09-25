#!/usr/bin/env python3
"""Measure threshold behaviour against fixture and real directories."""

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
from realdirs import coherent_folders  # noqa: E402

from messie.analyze import analyze, profile, vectorize  # noqa: E402
from messie.cluster import cluster_vectors  # noqa: E402
from messie.config import DEFAULT_SETTINGS  # noqa: E402
from messie.embed import get_embedder  # noqa: E402
from messie.result import Verdict  # noqa: E402
from messie.scan import read_dir, walk  # noqa: E402


@dataclass
class Separation:
    embedder: str
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
    embedder: str
    shipped_scale: float
    best: SweepPoint
    validation: SweepPoint
    training_topics: int
    validation_topics: int
    points: list[SweepPoint]
    validation_points: list[SweepPoint]


@dataclass
class RatioPoint:
    ratio: float
    caught: float      # of the cases that should fire, how many did
    false_alarms: float  # of the cases that should stay quiet, how many fired

    @property
    def total(self) -> float:
        return self.caught + (1.0 - self.false_alarms)


MIN_NEGATIVES = 20


@dataclass
class RatioSweep:
    name: str
    embedder: str
    shipped: float
    best: RatioPoint
    plateau: tuple[float, float]
    recommended: float
    positives: int
    negatives: int
    points: list[RatioPoint]

    @property
    def inconclusive(self) -> bool:
        """Return whether the sweep has too few negatives."""
        return self.negatives < MIN_NEGATIVES


def measure_separation(top: int = 6) -> Separation:
    """Measure within- and between-subject similarity."""
    embedder = get_embedder()
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
        embedder=embedder.name,
        intra_min=min(intra.values()),
        intra_median=statistics.median(intra.values()),
        inter_median=statistics.median(values),
        inter_p95=float(np.percentile(values, 95)),
        inter_max=max(values),
        closest_pairs=[(a, b, round(v, 3)) for v, a, b in inter[:top]],
    )


def sweep_threshold(*, pairs: int = 90, topics: int = 0, seed: int = 4) -> Sweep:
    """Find a clustering threshold for the fixture corpus."""
    chosen = sorted(ALL_TOPICS)[:topics] if topics else sorted(ALL_TOPICS)
    if len(chosen) < 4:
        raise ValueError("threshold calibration needs at least four topics")
    rng = random.Random(seed)
    rng.shuffle(chosen)
    split = max(2, min(len(chosen) - 2, round(len(chosen) * 0.75)))
    training_topics = chosen[:split]
    validation_topics = chosen[split:]
    embedder = get_embedder()
    tmp = Path(tempfile.mkdtemp(prefix="messie-calibrate-"))

    def fixtures(label: str, topic_names: list[str]):
        single = {}
        for topic in topic_names:
            folder = build_coherent(tmp / label / "one" / topic, topic, 6)
            single[topic] = vectorize(read_dir(folder).files, embedder=embedder).vectors

        combos = list(itertools.combinations(topic_names, 2))
        rng.shuffle(combos)
        both = {}
        for a, b in combos[:pairs]:
            folder = build_mixed(tmp / label / "two" / f"{a}__{b}", {a: 5, b: 5})
            files = read_dir(folder).files
            stems_a = {stem for stem, _ in TOPICS[a]}
            origin = np.array([0 if f.stem in stems_a else 1 for f in files])
            both[(a, b)] = (vectorize(files, embedder=embedder).vectors, origin)
        return single, both

    training = fixtures("training", training_topics)
    validation = fixtures("validation", validation_topics)

    def measure(threshold: float, cases) -> SweepPoint:
        single, both = cases
        def meaningful_groups(vectors: np.ndarray):
            clustering = cluster_vectors(vectors, threshold)
            floor = max(
                DEFAULT_SETTINGS.meaningful_cluster_min,
                int(DEFAULT_SETTINGS.meaningful_cluster_frac * len(vectors)),
            )
            return [group for group in clustering.groups if len(group) >= floor]

        # Match the meaningful groups consumed by signals.
        held = sum(1 for v in single.values() if len(meaningful_groups(v)) <= 1)
        apart = 0
        for vectors, origin in both.values():
            groups = meaningful_groups(vectors)
            merged = any(
                np.count_nonzero(origin[members] == 0) >= 2
                and np.count_nonzero(origin[members] == 1) >= 2
                for members in groups
            )
            apart += not merged
        return SweepPoint(
            threshold=round(float(threshold), 3),
            scale=round(float(threshold) / DEFAULT_SETTINGS.cluster_rel, 3),
            subjects_held=round(held / max(1, len(single)), 3),
            pairs_separated=round(apart / max(1, len(both)), 3),
        )

    thresholds = [float(t) for t in np.arange(0.10, 0.50, 0.01)]
    points = [measure(t, training) for t in thresholds]
    validation_points = [measure(t, validation) for t in thresholds]
    shipped_threshold = float(embedder.scale) * DEFAULT_SETTINGS.cluster_rel
    best = max(points, key=lambda p: (p.total, -abs(p.threshold - shipped_threshold)))
    heldout = min(validation_points, key=lambda p: abs(p.threshold - best.threshold))

    return Sweep(
        embedder=embedder.name,
        shipped_scale=float(embedder.scale),
        best=best,
        validation=heldout,
        training_topics=len(training_topics),
        validation_topics=len(validation_topics),
        points=points,
        validation_points=validation_points,
    )


def _standard_error(point: RatioPoint, npos: int, nneg: int) -> float:
    """Sampling error for a two-rate score."""
    def var(p: float, n: int) -> float:
        return p * (1.0 - p) / max(1, n)

    return float(np.sqrt(var(point.caught, npos) + var(point.false_alarms, nneg)))


def _plateau_of(points: list[RatioPoint], npos: int, nneg: int) -> tuple[float, float]:
    """Return the contiguous near-best range."""
    best = max(points, key=lambda p: p.total)
    slack = _standard_error(best, npos, nneg)
    keep = {p.ratio for p in points if p.total >= best.total - slack}
    ordered = [p.ratio for p in points]

    i = j = ordered.index(best.ratio)
    while i > 0 and ordered[i - 1] in keep:
        i -= 1
    while j < len(ordered) - 1 and ordered[j + 1] in keep:
        j += 1
    return (round(ordered[i], 3), round(ordered[j], 3))


def _summarise(name: str, embedder: str, shipped: float, rows, npos: int, nneg: int) -> RatioSweep:
    points = [
        RatioPoint(ratio=round(float(r), 3), caught=round(c, 3), false_alarms=round(f, 3))
        for r, c, f in rows
    ]
    plateau = _plateau_of(points, npos, nneg)
    return RatioSweep(
        name=name,
        embedder=embedder,
        shipped=shipped,
        best=max(points, key=lambda p: p.total),
        plateau=plateau,
        recommended=round((plateau[0] + plateau[1]) / 2, 2),
        positives=npos,
        negatives=nneg,
        points=points,
    )


def _fires(analysis, code: str) -> bool:
    return any(f.code == code for f in analysis.findings)


def sweep_unrelated(*, pairs: int = 60, seed: int = 4, limit: int = 400) -> RatioSweep:
    """Measure unrelated-topic recall and false alarms."""
    embedder = get_embedder()
    topics = sorted(ALL_TOPICS)
    tmp = Path(tempfile.mkdtemp(prefix="messie-unrelated-"))
    should_fire = []
    rng = random.Random(seed)
    combos = list(itertools.combinations(topics, 2))
    rng.shuffle(combos)
    for a, b in combos[:pairs]:
        contents = read_dir(build_mixed(tmp / "two" / f"{a}__{b}", {a: 6, b: 6}))
        should_fire.append((contents, vectorize(contents.files, embedder=embedder)))

    should_not = []
    for folder in coherent_folders(limit):
        try:
            contents = read_dir(folder)
            if len(contents.files) < DEFAULT_SETTINGS.min_files_to_judge:
                continue
            should_not.append((contents, vectorize(contents.files, embedder=embedder)))
        except Exception:  # noqa: BLE001 - unreadable tree, skip it
            continue

    rows = []
    at_risk_seen = 0
    for ratio in np.arange(0.20, 1.01, 0.05):
        settings = DEFAULT_SETTINGS.with_(unrelated_rel=float(ratio))
        caught = sum(
            _fires(
                analyze(c, embedder=embedder, settings=settings, child_profiles={}, precomputed=r),
                "unrelated_topics",
            )
            for c, r in should_fire
        )
        at_risk = alarms = 0
        for c, r in should_not:
            analysis = analyze(
                c, embedder=embedder, settings=settings, child_profiles={}, precomputed=r
            )
            if analysis.meaningful_clusters < 2:
                continue
            at_risk += 1
            alarms += _fires(analysis, "unrelated_topics")
        at_risk_seen = max(at_risk_seen, at_risk)
        rows.append((ratio, caught / max(1, len(should_fire)), alarms / max(1, at_risk)))

    return _summarise(
        "unrelated_rel",
        embedder.name,
        DEFAULT_SETTINGS.unrelated_rel,
        rows,
        len(should_fire),
        at_risk_seen,
    )


def sweep_misfiled(*, depth: int = 3, limit: int = 400) -> RatioSweep:
    """Measure the misfiled-neighbour margin."""
    from corpus.build import build_nested_misfile

    embedder = get_embedder()
    tmp = Path(tempfile.mkdtemp(prefix="messie-misfiled-"))

    def prepare(root: Path):
        """Read and embed one folder plus the profiles of everything below it."""
        contents = read_dir(root)
        profiles = {}
        for sub in walk(root, DEFAULT_SETTINGS):
            key = sub.path.resolve()
            if key == root.resolve():
                continue
            if len(sub.files) >= DEFAULT_SETTINGS.meaningful_cluster_min:
                profiles[key] = profile(sub.files, embedder=embedder)
        return contents, profiles, vectorize(contents.files, embedder=embedder)

    topics = sorted(ALL_TOPICS)
    positives = []
    for i in range(0, len(topics) - 1, 2):
        root = build_nested_misfile(
            tmp / f"nest_{topics[i]}", topics[i], topics[i + 1], depth=depth
        )
        positives.append(prepare(root))

    candidates = []
    for folder in coherent_folders(limit):
        try:
            contents, profiles, record = prepare(folder)
        except Exception:  # noqa: BLE001 - unreadable tree, skip it
            continue
        if profiles and len(contents.files) >= DEFAULT_SETTINGS.min_files_to_judge:
            candidates.append((contents, profiles, record))

    permissive_settings = DEFAULT_SETTINGS.with_(misfiled_margin_rel=0.0)
    negatives = [
        case
        for case in candidates
        if _fires(
            analyze(
                case[0],
                embedder=embedder,
                settings=permissive_settings,
                child_profiles=case[1],
                precomputed=case[2],
            ),
            "misfiled_neighbours",
        )
    ]

    rows = []
    for ratio in np.arange(0.0, 0.81, 0.05):
        settings = DEFAULT_SETTINGS.with_(misfiled_margin_rel=float(ratio))
        caught = sum(
            _fires(
                analyze(c, embedder=embedder, settings=settings, child_profiles=pr, precomputed=r),
                "misfiled_neighbours",
            )
            for c, pr, r in positives
        )
        alarms = sum(
            _fires(
                analyze(c, embedder=embedder, settings=settings, child_profiles=pr, precomputed=r),
                "misfiled_neighbours",
            )
            for c, pr, r in negatives
        )
        rows.append(
            (ratio, caught / max(1, len(positives)), alarms / max(1, len(negatives)))
        )

    return _summarise(
        "misfiled_margin_rel",
        embedder.name,
        DEFAULT_SETTINGS.misfiled_margin_rel,
        rows,
        len(positives),
        len(negatives),
    )


def measure_real_world(limit: int = 90) -> RealWorld:
    """Measure findings on real directories."""
    from messie.analyze import analyze_dir

    judged = messy = 0
    by_signal: dict[str, int] = {}
    offenders: list[tuple[str, list[str]]] = []
    for folder in coherent_folders(limit):
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


def _print_separation(report: Separation) -> None:
    print(f"\nSEPARATION · {report.embedder}")
    print(f"  within a subject   min {report.intra_min:.3f}   median {report.intra_median:.3f}")
    print(
        f"  between subjects   median {report.inter_median:.3f}   "
        f"p95 {report.inter_p95:.3f}   max {report.inter_max:.3f}"
    )
    print("  closest pairs:")
    for a, b, value in report.closest_pairs:
        print(f"      {value:.3f}  {a} ~ {b}")


def _print_sweep(report: Sweep) -> None:
    print(f"\nTHRESHOLD SWEEP · {report.embedder}")
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
    heldout = report.validation
    print(
        f"  held-out topics {report.validation_topics}  "
        f"subjects {heldout.subjects_held:.0%}, pairs {heldout.pairs_separated:.0%}"
    )
    print(f"  shipped scale  {report.shipped_scale:.2f}", end="")
    drift = abs(report.shipped_scale - best.scale)
    print("   ok" if drift <= 0.06 else f"   DRIFTED by {drift:.2f} — update WordLlama")


def _print_ratio(report: RatioSweep) -> None:
    print(f"\n{report.name.upper()} · {report.embedder}")
    print(
        f"  {report.positives} cases that should fire, "
        f"{report.negatives} at risk of a false alarm"
    )
    print(f"  {'ratio':>7} {'caught':>9} {'false alarms':>14} {'score':>8}")
    for point in report.points:
        mark = "  <- best" if point is report.best else ""
        print(
            f"  {point.ratio:>7.2f} {point.caught:>8.0%} "
            f"{point.false_alarms:>13.0%} {point.total:>8.3f}{mark}"
        )
    lo, hi = report.plateau
    error = _standard_error(report.best, report.positives, report.negatives)
    print(
        f"  plateau {lo:.2f}-{hi:.2f} (within 1 s.e. = {error:.3f} of the peak), "
        f"midpoint {report.recommended:.2f}"
    )
    if report.inconclusive:
        print(
            f"  only {report.negatives} negatives at risk (want {MIN_NEGATIVES}+) — "
            "the false-alarm column is noise"
        )
        print(
            f"  shipped {report.shipped:.2f}   INCONCLUSIVE — leave it alone until "
            "there are more negatives to measure against"
        )
        return
    print(f"  shipped {report.shipped:.2f}", end="")
    drift = abs(report.shipped - report.recommended)
    if lo <= report.shipped <= hi:
        print("   ok — on the plateau")
    else:
        print(f"   OFF the plateau by {drift:.2f} — update config.py")


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
    parser.add_argument(
        "--sections", default="separation,sweep,realworld",
        help="comma-separated subset to run",
    )
    parser.add_argument("--pairs", type=int, default=90, help="subject pairs in the sweep")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    wanted = {s.strip() for s in args.sections.split(",")}
    out: dict[str, Separation | Sweep | RatioSweep | RealWorld] = {}

    if "separation" in wanted:
        out["separation"] = measure_separation()
    if "sweep" in wanted:
        out["sweep"] = sweep_threshold(pairs=args.pairs)
    if "unrelated" in wanted:
        out["unrelated"] = sweep_unrelated(pairs=min(args.pairs, 60))
    if "misfiled" in wanted:
        out["misfiled"] = sweep_misfiled()
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
    for key in ("unrelated", "misfiled"):
        if key in out:
            _print_ratio(out[key])  # type: ignore[arg-type]
    if "realworld" in out:
        _print_real_world(out["realworld"])  # type: ignore[arg-type]
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
