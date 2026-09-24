"""Tunable thresholds. Every magic number in messie lives here."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

# Directories that are somebody else's business: package caches, VCS internals,
# OS-managed trees. Their internal chaos is not the user's mess.
IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git", ".hg", ".svn", ".bzr",
        "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        ".venv", "venv", "env", ".tox", ".nox", "site-packages", ".eggs",
        "dist", "build", "target", ".next", ".nuxt", ".parcel-cache", ".gradle",
        ".idea", ".vscode", ".vs", ".cache", ".local", ".config",
        "Library", "AppData", "Application Data", "System Volume Information",
        "$RECYCLE.BIN", ".Trash", ".Trashes", ".DS_Store", "Photos Library.photoslibrary",
    }
)


@dataclass(frozen=True)
class Settings:
    """Analysis parameters.

    The similarity numbers are cosine similarities between unit vectors. They
    are calibrated against static embeddings, where same-topic pairs land around
    0.35-0.55 and unrelated pairs hover near 0.0.
    """

    # --- scanning -----------------------------------------------------------
    max_depth: int = 3
    include_hidden: bool = False
    follow_symlinks: bool = False
    max_files_per_dir: int = 2000
    ignore_dirs: frozenset[str] = IGNORE_DIRS
    extra_ignores: frozenset[str] = field(default_factory=frozenset)

    # A folder needs some substance before calling it messy means anything.
    min_files_to_judge: int = 6

    # --- content ------------------------------------------------------------
    #: Measured, not chosen: embedding cost scales with how much text each
    #: file contributes, and past a point the extra text changes no verdicts.
    #: Across three real trees (site-packages, the CPython stdlib, this repo —
    #: 395 judged folders) dropping 4000 to 2500 left every single verdict
    #: identical and cut a walk by about 27%. 1500 was faster still and moved
    #: one folder in 221, which is why this sits at 2500 rather than lower.
    text_excerpt_chars: int = 2500
    max_read_bytes: int = 1 << 20  # never read more than 1 MiB off disk per file
    # Below this much extracted text, lean on the filename instead of content.
    min_text_chars: int = 120

    # How much the content vector counts relative to the filename vector.
    text_weight_rich: float = 0.75
    text_weight_thin: float = 0.45

    # --- clustering ---------------------------------------------------------
    # Backends disagree about what a "high" cosine is: hashed TF-IDF put
    # same-topic pairs around 0.15 where wordllama puts them near 0.40. Only
    # one backend ships today, so this indirection buys nothing right now —
    # it is kept because it is what lets a candidate backend be measured
    # against the incumbent at all. Fixing the cut-offs absolutely would mean
    # every future comparison ran at a threshold tuned for the wrong model.
    #
    # Each ratio below says what it was fitted against; see scripts/calibrate.py.
    #: Pins the clustering cut-off absolutely, overriding the scale-relative
    #: derivation. Set by --threshold.
    cluster_threshold_override: float | None = None

    #: Fitted by ``calibrate.py --sections sweep``: the clustering cut-off that
    #: best holds corpus subjects together while keeping unrelated ones apart.
    cluster_rel: float = 0.65

    #: Swept by ``calibrate.py --sections unrelated``, and deliberately NOT
    #: set to what that sweep points at. Worth reading before touching.
    #:
    #: The sweep's peak is 0.30. Two separate things argue for staying here.
    #:
    #: First, the negative set is real package directories, and the README has
    #: always declined to tune to them: a large library genuinely does hold
    #: several subjects, so a finding on one is not plainly wrong. On this
    #: machine only nine of 431 real directories can raise the finding at all,
    #: which is why the sweep reports itself inconclusive rather than
    #: recommending a value — nine cases cannot support one.
    #:
    #: Second, and decisive: moving to 0.30 costs recall on genuinely mixed
    #: folders, 98% down to 92% on the corpus and further below that, and the
    #: repo's own ground-truth tests are where it lands. At 0.30 the canonical
    #: "my novel and my tax returns are in one folder" case stops being called
    #: a mess at all. That case is the reason this tool exists, so the sweep's
    #: equal weighting of a miss against a false alarm is the wrong objective
    #: here rather than the wrong measurement.
    #:
    #: Revisit if the false-alarm rate on *personal* folders is ever measured.
    #: That is the sample this constant should answer to, and it does not exist
    #: yet — every negative available is somebody's installed library.
    unrelated_rel: float = 0.55

    #: NOT fitted — ``calibrate.py --sections misfiled`` reports it
    #: inconclusive and refuses to recommend. Only ten real directories on a
    #: full scan can raise this finding at all, because the dominant-subject
    #: gate in ``misfiled_neighbours`` already suppresses the rest, so the
    #: false-alarm column is ten coin flips. The sweep's nominal optimum of
    #: 0.75 would cost more than half the recall to chase it. Left at the
    #: original guess until there is a sample worth fitting against.
    misfiled_margin_rel: float = 0.25

    # A cluster is "meaningful" at 3+ files, or at this share of the folder.
    meaningful_cluster_min: int = 3
    meaningful_cluster_frac: float = 0.10
    near_duplicate_sim: float = 0.97

    # --- signal thresholds --------------------------------------------------
    #: Off by default, and the only signal that has to be asked for.
    #:
    #: ``overcrowded`` is the one signal that never looks inside the files. It
    #: counts them, which is exactly the judgement messie exists to argue
    #: against: a folder holding one thing is not a mess for holding a lot of
    #: it. Measured over a real workspace of 254 judged folders, it fired on 34
    #: and was the *only* finding on 26 of those — every large one being 100%
    #: a single kind, one or two extensions, and a single cluster. Camera
    #: rolls, image datasets, log directories. Sixteen of the 26 were already
    #: TIDY, so the signal spoke and changed nothing; the other ten it pushed
    #: to LIVED-IN on no evidence of mess at all.
    #:
    #: Where a crowded folder really is a mess, the content signals say so
    #: independently — in the eight folders here where it fired alongside
    #: something else, that something else had already made the case. So this
    #: was carrying almost no unique signal and a lot of noise.
    #:
    #: Kept rather than deleted because "this folder has 900 files in it" is a
    #: fair thing to want to be told; it is just not evidence of mess. ``-c`` /
    #: ``--crowding`` turns it on.
    report_crowding: bool = False
    overcrowded_soft_limit: int = 40
    time_strata_gap_days: float = 365.0

    # --- scoring ------------------------------------------------------------
    #: Read-only on purpose. ``Settings`` is frozen, but ``with_()`` hands the
    #: same dict to the copy, so a plain dict here means mutating one settings
    #: object silently rewrites every other one derived from it.
    signal_weights: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType({
            "unrelated_topics": 1.00,
            # Two wordings of one signal at different intensities, so they must
            # weigh the same: otherwise the score would jump at the point where
            # "some files do not belong" becomes "nothing here belongs".
            #
            # Set near unrelated_topics rather than between the two weights this
            # replaced. The severity ramp already keeps a handful of strays mild;
            # the weight governs the far end, where nothing in the folder relates
            # to anything, and that deserves to rank with "four unrelated things
            # are living here" rather than below it.
            "no_common_thread": 0.85,
            "strays": 0.85,
            "misfiled_neighbours": 0.60,
            "time_strata": 0.40,
            "overcrowded": 0.40,
            "debris": 0.35,
            "version_pileups": 0.35,
            "duplicates": 0.30,
        })
    )

    def with_(self, **kwargs) -> Settings:
        """Return a copy with fields overridden."""
        return replace(self, **kwargs)

    def is_ignored_dir(self, name: str) -> bool:
        return name in self.ignore_dirs or name in self.extra_ignores


@dataclass(frozen=True)
class Thresholds:
    """Absolute similarity cut-offs, resolved against a backend's scale."""

    scale: float
    cluster: float
    unrelated: float
    misfiled_margin: float
    near_duplicate: float

    @classmethod
    def derive(
        cls, scale: float, settings: Settings, override: float | None = None
    ) -> Thresholds:
        """Cut-offs for a backend whose same-topic similarity sits near ``scale``.

        ``override`` pins the clustering cut-off directly; the others move with
        it so their relationship stays intact.
        """
        cluster = override if override is not None else scale * settings.cluster_rel
        ratio = cluster / (scale * settings.cluster_rel) if scale else 1.0
        return cls(
            scale=scale,
            cluster=cluster,
            unrelated=scale * settings.unrelated_rel * ratio,
            misfiled_margin=scale * settings.misfiled_margin_rel * ratio,
            near_duplicate=settings.near_duplicate_sim,
        )


DEFAULT_SETTINGS = Settings()
