"""Document-facing helpers used by the Streamlit UI."""

from qdrant_client.models import FieldCondition, Filter, MatchValue

from ragagent.storage.qdrant_store import QdrantStorage


def list_available_sources() -> list[str]:
    """Return currently stored source IDs for UI filtering."""
    documents, error = load_document_summaries()
    if error:
        return []
    return sorted(
        {
            doc.get("source", "")
            for doc in documents
            if doc.get("source", "")
        }
    )


def load_document_summaries() -> tuple[list[dict], str | None]:
    """Load current document summaries from Qdrant for the explorer panel."""
    try:
        return QdrantStorage().list_documents(), None
    except Exception as exc:  # pragma: no cover - UI fallback only
        return [], str(exc)


def delete_document(doc_id: str) -> str | None:
    """Delete one document and its chunks from Qdrant."""
    try:
        store = QdrantStorage()
        if hasattr(store, "delete_document"):
            store.delete_document(doc_id)
        else:  # pragma: no cover - defensive fallback for stale hot-reload state
            store.client.delete(
                collection_name=store.collection,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=doc_id),
                        )
                    ]
                ),
            )
        return None
    except Exception as exc:  # pragma: no cover - UI fallback only
        return str(exc)
