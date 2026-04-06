"""Compatibility shim for the Streamlit app entrypoint."""

from pathlib import Path
import sys

_SRC_PATH = Path(__file__).resolve().parent / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from ragagent.app.streamlit_app import *  # noqa: F401,F403
