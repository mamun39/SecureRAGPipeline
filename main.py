"""Compatibility shim for the FastAPI and Inngest app entrypoint."""

from pathlib import Path
import sys

_SRC_PATH = Path(__file__).resolve().parent / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from ragagent.app.inngest_app import app, inngest_client, rag_inngest_pdf, rag_query_pdf_ai

__all__ = ["app", "inngest_client", "rag_inngest_pdf", "rag_query_pdf_ai"]
