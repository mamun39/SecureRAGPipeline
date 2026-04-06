"""Compatibility re-exports for safe context helpers."""

from pathlib import Path
import sys

_SRC_PATH = Path(__file__).resolve().parent / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from ragagent.security.safe_context import *  # noqa: F401,F403
