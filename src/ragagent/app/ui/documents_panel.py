"""Documents panel for the Streamlit UI."""

import streamlit as st

from ..services.document_service import load_document_summaries


def render_documents_panel() -> None:
    """Render the document explorer from stored Qdrant metadata."""
    st.subheader("Documents")
    st.caption("Browse stored document metadata as it currently exists in Qdrant.")

    documents, document_error = load_document_summaries()
    if document_error:
        st.warning(f"Could not load document summaries from Qdrant: {document_error}")
        return

    if not documents:
        st.caption("No stored documents found in Qdrant yet.")
        return

    docs_col1, docs_col2 = st.columns(2)
    docs_col1.metric("Stored documents", len(documents))
    docs_col2.metric("Stored chunks", sum(doc["chunk_count"] for doc in documents))
    st.dataframe(
        documents,
        width="stretch",
        hide_index=True,
        column_order=[
            "source",
            "doc_id",
            "classification",
            "trust_level",
            "ingest_decision",
            "chunk_count",
            "created_at",
            "ingest_scan_flags",
        ],
    )
