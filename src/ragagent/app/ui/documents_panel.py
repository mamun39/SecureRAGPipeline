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

    classifications = sorted({doc.get("classification", "internal") for doc in documents})
    trust_levels = sorted({doc.get("trust_level", "user_uploaded") for doc in documents})
    ingest_decisions = sorted({doc.get("ingest_decision", "allow") for doc in documents})

    filter_col1, filter_col2 = st.columns(2)
    source_query = filter_col1.text_input("Search source/doc", key="documents_source_query").strip().lower()
    selected_classifications = filter_col2.multiselect(
        "Classification",
        options=classifications,
        default=classifications,
        key="documents_classification_filter",
    )

    filter_col3, filter_col4 = st.columns(2)
    selected_trust_levels = filter_col3.multiselect(
        "Trust level",
        options=trust_levels,
        default=trust_levels,
        key="documents_trust_filter",
    )
    selected_decisions = filter_col4.multiselect(
        "Ingest decision",
        options=ingest_decisions,
        default=ingest_decisions,
        key="documents_decision_filter",
    )

    filtered_documents = [
        doc
        for doc in documents
        if (not source_query or source_query in doc.get("source", "").lower() or source_query in doc.get("doc_id", "").lower())
        and doc.get("classification", "internal") in selected_classifications
        and doc.get("trust_level", "user_uploaded") in selected_trust_levels
        and doc.get("ingest_decision", "allow") in selected_decisions
    ]

    docs_col1, docs_col2 = st.columns(2)
    docs_col1.metric("Visible documents", len(filtered_documents))
    docs_col2.metric("Visible chunks", sum(doc["chunk_count"] for doc in filtered_documents))

    if not filtered_documents:
        st.caption("No documents match the current filters.")
        return

    st.dataframe(
        filtered_documents,
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
