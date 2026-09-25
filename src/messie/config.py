"""Analysis settings and derived thresholds."""

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
    max_depth: int = 3
    include_hidden: bool = False
    follow_symlinks: bool = False
    max_files_per_dir: int = 2000
    ignore_dirs: frozenset[str] = IGNORE_DIRS
    extra_ignores: frozenset[str] = field(default_factory=frozenset)

    min_files_to_judge: int = 6

    text_excerpt_chars: int = 1000
    max_read_bytes: int = 1 << 20
    min_text_chars: int = 120
    image_description_sample: int = 24

    text_weight_rich: float = 0.75
    text_weight_thin: float = 0.45

    cluster_threshold_override: float | None = None
    cluster_rel: float = 0.65
    unrelated_rel: float = 0.55
    misfiled_margin_rel: float = 0.25
    meaningful_cluster_min: int = 3
    meaningful_cluster_frac: float = 0.10
    near_duplicate_sim: float = 0.97

    report_crowding: bool = False
    overcrowded_soft_limit: int = 40
    time_strata_gap_days: float = 365.0

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
    """Absolute similarity cut-offs, resolved against an embedder's scale."""

    scale: float
    cluster: float
    unrelated: float
    misfiled_margin: float
    near_duplicate: float

    @classmethod
    def derive(
        cls, scale: float, settings: Settings, override: float | None = None
    ) -> Thresholds:
        """Cut-offs for an embedder whose same-topic similarity sits near ``scale``.
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
