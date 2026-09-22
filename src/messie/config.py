"""Tunable thresholds. Every magic number in messie lives here."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

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
    text_excerpt_chars: int = 4000
    max_read_bytes: int = 1 << 20  # never read more than 1 MiB off disk per file
    # Below this much extracted text, lean on the filename instead of content.
    min_text_chars: int = 120

    # How much the content vector counts relative to the filename vector.
    text_weight_rich: float = 0.75
    text_weight_thin: float = 0.45

    # --- clustering ---------------------------------------------------------
    # Backends disagree about what a "high" cosine is: hashed TF-IDF puts
    # same-topic pairs around 0.15 where a static-embedding model puts them
    # near 0.40. So thresholds are expressed as fractions of each backend's
    # own same-topic scale, and one set of numbers works for all of them.
    #: Pins the clustering cut-off absolutely, overriding the scale-relative
    #: derivation. Set by --threshold.
    cluster_threshold_override: float | None = None
    cluster_rel: float = 0.65
    unrelated_rel: float = 0.55
    stray_rel: float = 0.45
    misfiled_margin_rel: float = 0.25

    # A cluster is "meaningful" at 3+ files, or at this share of the folder.
    meaningful_cluster_min: int = 3
    meaningful_cluster_frac: float = 0.10
    near_duplicate_sim: float = 0.97

    # --- signal thresholds --------------------------------------------------
    overcrowded_soft_limit: int = 40
    type_soup_entropy_floor: float = 0.35
    time_strata_gap_days: float = 365.0

    # --- scoring ------------------------------------------------------------
    signal_weights: dict[str, float] = field(
        default_factory=lambda: {
            "unrelated_topics": 1.00,
            "no_common_thread": 0.70,
            "misfiled_neighbours": 0.60,
            "strays": 0.55,
            "type_soup": 0.50,
            "time_strata": 0.40,
            "overcrowded": 0.40,
            "debris": 0.35,
            "version_pileups": 0.35,
            "duplicates": 0.30,
        }
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
    stray: float
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
            stray=scale * settings.stray_rel * ratio,
            misfiled_margin=scale * settings.misfiled_margin_rel * ratio,
            near_duplicate=settings.near_duplicate_sim,
        )


DEFAULT_SETTINGS = Settings()
