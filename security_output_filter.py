"""Compatibility re-exports for output filtering."""

from pathlib import Path
import sys

_SRC_PATH = Path(__file__).resolve().parent / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from ragagent.security.output_filter import *  # noqa: F401,F403
