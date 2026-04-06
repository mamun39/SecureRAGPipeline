"""Document-facing helpers used by the Streamlit UI."""

from pathlib import Path

from ragagent.storage.qdrant_store import QdrantStorage


def list_available_sources() -> list[str]:
    """Return currently available source IDs for UI filtering."""
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        return []
    return sorted({path.name for path in uploads_dir.glob("*.pdf") if path.is_file()})


def load_document_summaries() -> tuple[list[dict], str | None]:
    """Load current document summaries from Qdrant for the explorer panel."""
    try:
        return QdrantStorage().list_documents(), None
    except Exception as exc:  # pragma: no cover - UI fallback only
        return [], str(exc)
