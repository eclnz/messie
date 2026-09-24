"""Find folders whose contents have no common thread."""

from messie.analyze import analyze_dir, analyze_tree
from messie.result import DirAnalysis, Finding, SkipReason, Verdict

__all__ = ["DirAnalysis", "Finding", "SkipReason", "Verdict", "analyze_dir", "analyze_tree"]
__version__ = "0.1.0"
