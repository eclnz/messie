"""Tunable thresholds. Every magic number in messie lives here."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

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
    # Screening more text takes longer.
    text_excerpt_chars: int = 2500
    max_read_bytes: int = 1 << 20  # never read more than 1 MiB off disk per file
    # Below this much extracted text, lean on the filename instead of content.
    min_text_chars: int = 120

    # How much the content vector counts relative to the filename vector.
    text_weight_rich: float = 0.75
    text_weight_thin: float = 0.45

    # --- clustering ---------------------------------------------------------

    cluster_threshold_override: float | None = None

    #: Fitted by ``calibrate.py --sections sweep``: the clustering cut-off that
    #: best holds corpus subjects together while keeping unrelated ones apart.
    cluster_rel: float = 0.65

    #: Swept by ``calibrate.py --sections unrelated``, and deliberately NOT
    #: set to what that sweep points at. Worth reading before touching.
    unrelated_rel: float = 0.55

    #: NOT fitted — ``calibrate.py --sections misfiled`` reports it
    #: inconclusive and refuses to recommend.
    misfiled_margin_rel: float = 0.25

    # A cluster is "meaningful" at 3+ files, or at this share of the folder.
    meaningful_cluster_min: int = 3
    meaningful_cluster_frac: float = 0.10
    near_duplicate_sim: float = 0.97

    # --- signal thresholds --------------------------------------------------
    #: Off by default, and the only signal that has to be asked for. 
    # ``-c / --crowding`` turns it on.
    report_crowding: bool = False
    overcrowded_soft_limit: int = 40
    time_strata_gap_days: float = 365.0

    # --- scoring ------------------------------------------------------------
    signal_weights: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType({
            "unrelated_topics": 1.00,
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
