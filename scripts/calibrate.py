#!/usr/bin/env python3
"""Measure what the algorithm actually does, instead of reasoning about it.

Every structural bug in messie so far was found by printing numbers: comparing
normalised centroids inflated similarity and welded unrelated subjects
together; the embedder scale was guessed from a four-document probe and was
badly wrong; a CSV saved as .txt read as gibberish because extraction was
discarding line breaks. None of that was visible in the code. All of it was
obvious in a table.

Those measurements used to be throwaway scripts. This is them made permanent,
so the constants in the source have a derivation anyone can re-run:

    python scripts/calibrate.py                 # everything, default embedder
    python scripts/calibrate.py --sections unrelated,misfiled
    python scripts/calibrate.py --json          # for machines

Sections:

    separation   how far apart the corpus subjects are
    sweep        which clustering threshold best separates them, and the
                 embedder scale that threshold implies
    unrelated    where to put ``unrelated_rel``: the point at which two groups
                 stop being two facets of one subject and start being two
                 subjects sharing a folder
    misfiled     where to put ``misfiled_margin_rel``: how much better a
                 subfolder must fit a file than its own folder does, before
                 saying so is worth the risk of being wrong
    realworld    how often real, coherent directories on this machine are
                 wrongly called messy — the only sample nobody authored to
                 suit the tool

Each sweep reports a *plateau* as well as a peak. A constant sitting on a cliff
edge is a constant that will be wrong on the next corpus, so where the optimum
is flat these prefer its middle to its maximum.

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
from realdirs import coherent_folders  # noqa: E402

from messie.cluster import cluster_vectors  # noqa: E402
from messie.config import DEFAULT_SETTINGS  # noqa: E402
from messie.embed import get_embedder  # noqa: E402
from messie.analyze import analyze, profile, vectorize  # noqa: E402
from messie.scan import read_dir, walk  # noqa: E402
from messie.result import Verdict  # noqa: E402

# --- reports ---------------------------------------------------------------


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
    points: list[SweepPoint]


@dataclass
class RatioPoint:
    """One value of a scale-relative ratio, and what it costs on each side."""

    ratio: float
    caught: float      # of the cases that should fire, how many did
    false_alarms: float  # of the cases that should stay quiet, how many fired

    @property
    def total(self) -> float:
        return self.caught + (1.0 - self.false_alarms)


#: Below this many at-risk negatives, a false-alarm rate is noise. Both
#: ratios here were first measured against sets that fell short of it — one of
#: them against a set of zero — and both times the resulting plateau looked
#: convincing and meant nothing.
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
        """Too few negatives at risk for the false-alarm column to mean anything.

        A sweep in this state must not move a constant. Its peak is wherever
        the handful of negatives happened to fall, and following it would trade
        away real recall to chase noise.
        """
        return self.negatives < MIN_NEGATIVES


# --- measurement -----------------------------------------------------------


def measure_separation(top: int = 6) -> Separation:
    """Average-link similarity within each subject, and between every pair."""
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
    """Which clustering threshold best tells the corpus subjects apart.

    Two things are traded off. Too low and every subject stays whole but
    unrelated ones merge; too high and unrelated ones separate but real
    subjects shatter. The sum of the two rates is maximised at the crossover.
    """
    chosen = list(ALL_TOPICS)[:topics] if topics else list(ALL_TOPICS)
    embedder = get_embedder()
    tmp = Path(tempfile.mkdtemp(prefix="messie-calibrate-"))

    single = {}
    for topic in chosen:
        folder = build_coherent(tmp / "one" / topic, topic, 6)
        single[topic] = vectorize(read_dir(folder).files, embedder=embedder).vectors

    rng = random.Random(seed)
    combos = list(itertools.combinations(chosen, 2))
    rng.shuffle(combos)
    both = {}
    for a, b in combos[:pairs]:
        folder = build_mixed(tmp / "two" / f"{a}__{b}", {a: 5, b: 5})
        files = read_dir(folder).files
        stems_a = {stem for stem, _ in TOPICS[a]}
        origin = np.array([0 if f.stem in stems_a else 1 for f in files])
        both[(a, b)] = (vectorize(files, embedder=embedder).vectors, origin)

    points = []
    for threshold in np.arange(0.10, 0.50, 0.01):
        held = sum(1 for v in single.values() if len(cluster_vectors(v, threshold).groups) == 1)
        apart = 0
        for vectors, origin in both.values():
            clustering = cluster_vectors(vectors, threshold)
            merged = any(
                len(set(origin[members])) > 1
                for members in clustering.groups
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
        embedder=embedder.name,
        shipped_scale=float(embedder.scale),
        best=max(points, key=lambda p: p.total),
        points=points,
    )


# --- the scale-relative ratios ---------------------------------------------
#
# ``cluster_rel`` has its own sweep above, because the clustering cut-off is
# measurable without running a single signal. The other two only mean anything
# once a signal has spoken, so they are fitted the same way but against whether
# the right finding came out: build cases that should fire and cases that
# should stay quiet, then vary the ratio and count both.
#
# Vectors do not depend on either ratio, so every folder is read and embedded
# once and only ``analyze`` is re-run. That is the difference between a
# sweep that takes twenty seconds and one nobody bothers to run.


def _standard_error(point: RatioPoint, npos: int, nneg: int) -> float:
    """Sampling error on one point's score, from the two binomial rates.

    The score adds two proportions measured on different samples, so its error
    is the root of the sum of theirs. It matters: with 60 positives and ~34
    at-risk negatives, one standard error is around 0.11, and the first version
    of this sweep called a plateau at a slack of 0.02 — declaring a single
    point optimal when a dozen neighbouring values were indistinguishable from
    it. A tolerance tighter than the noise invents precision.
    """
    def var(p: float, n: int) -> float:
        return p * (1.0 - p) / max(1, n)

    return float(np.sqrt(var(point.caught, npos) + var(point.false_alarms, nneg)))


def _plateau_of(points: list[RatioPoint], npos: int, nneg: int) -> tuple[float, float]:
    """The contiguous run of ratios indistinguishable from the best one.

    "Indistinguishable" means within one standard error of the peak, not within
    some fixed slack. Reported because the midpoint of a wide plateau is a
    better constant than the argmax: it is the value that stays right when the
    corpus changes slightly, and every magic number in messie that had to be
    fixed twice was a number sitting next to a cliff.
    """
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
    """Where two groups stop being one subject and start being two.

    ``unrelated_rel`` is the ceiling on the similarity between two cluster
    centroids, below which they count as unrelated to each other. It decides
    whether ``unrelated_topics`` speaks at all.

    Both error modes are real and they pull opposite ways. Set it too high and
    a single subject the clusterer split into facets reads as two subjects
    cohabiting, which is the false alarm people mind most. Set it too low and a
    genuine pair of unrelated subjects is waved through as merely adjacent.

    Positives are two-subject folders from the corpus. Negatives are *real*
    directories — with a caveat that decides how this report should be read:
    they are package directories, and the project deliberately does not tune to
    them (see the README). A large library genuinely does hold several
    subjects, so a finding on one is not straightforwardly wrong. Treat the
    false-alarm column as an upper bound on the error rate, measured against
    the least favourable sample available, rather than as a defect count.

    They are used anyway because the synthetic coherent folders cannot serve.
    At six to eight files none of the 37 splits into two meaningful clusters,
    so not one is capable of producing this finding at any ratio, and scoring
    against them would have reported a spotless 0% across the whole range
    — a flat line that
    looks like a wide safe plateau and is really a measurement of nothing. Only
    a folder that actually got split is at risk, so only those are counted, and
    ``at_risk`` is reported so a vacuous negative set cannot hide again.

    ``limit`` is deliberately several times the 90 the other sections use. Only
    about one real directory in twelve splits into two meaningful clusters, and
    a rate over the handful that come out of 90 folders can only ever read 0%,
    50% or 100% — precise-looking numbers with no information in them.
    """
    embedder = get_embedder()
    topics = list(ALL_TOPICS)
    tmp = Path(tempfile.mkdtemp(prefix="messie-unrelated-"))
    should_fire = []
    rng = random.Random(seed)
    combos = list(itertools.combinations(topics, 2))
    rng.shuffle(combos)
    for a, b in combos[:pairs]:
        contents = read_dir(build_mixed(tmp / "two" / f"{a}__{b}", {a: 6, b: 6}))
        should_fire.append((contents, vectorize(contents.files, embedder=embedder)))

    # Real, coherent directories: one project, one purpose, so any
    # unrelated_topics finding on one of them is a false alarm.
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
    """How much better a subfolder must fit a file before we say so.

    ``misfiled_margin_rel`` is that margin: a loose file is only called
    misfiled when some subfolder beats the folder it is sitting in by this
    much. Zero margin flags anything marginally closer to a subfolder, which on
    real trees once meant a package flagging its own subpackages — the single
    largest source of false positives this tool has had.

    Positives come from ``build_nested_misfile``, which buries a subject a few
    levels down and leaves copies of it loose at the top. Negatives are real
    directories, the only sample where a false positive costs something and
    nobody arranged the files to suit us.

    A negative counts as *at risk* only if it fires at a margin of zero. A real
    directory with no subfolder worth comparing against — two in three of them
    — cannot produce this finding however the margin is set, and averaging it
    in would report a reassuring 0% that is really a statement about how many
    flat directories exist on this machine.
    """
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

    topics = list(ALL_TOPICS)
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

    # Which of them this signal can reach at all, at the most permissive margin.
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
    """Judge real directories that were not written for this test.

    A package directory is coherent by construction — one project, one purpose
    — so a high rate here means the thresholds fit the fixtures rather than the
    world. This is how ``garbled`` was caught: perfect on synthetic nonsense,
    wrong on every real file it flagged.
    """
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


# --- printing --------------------------------------------------------------


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
