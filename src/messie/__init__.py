"""messie — notices when a folder has become a mess.

messie never moves, renames or deletes anything, and never proposes a filing
scheme. Deciding what belongs where is the user's job. All it does is look at
what is actually in a folder and say, with evidence, whether unrelated things
have ended up living together.

Everything runs on this machine. No network calls are made during analysis.
"""

from messie.analyze import analyze_dir, analyze_tree
from messie.result import DirAnalysis
from messie.score import Verdict
from messie.signals import Finding

__all__ = ["DirAnalysis", "Finding", "Verdict", "analyze_dir", "analyze_tree"]
__version__ = "0.1.0"
