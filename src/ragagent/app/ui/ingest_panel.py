"""Ingestion panel for the Streamlit UI."""

import asyncio
from pathlib import Path

import streamlit as st

from ..services.inngest_service import send_rag_ingest_event, wait_for_run_output
from ...security.audit import log_security_event


def save_uploaded_pdf(file) -> Path:
    """Save an uploaded PDF to disk and return its local path."""
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())
    return file_path


def render_ingest_panel() -> None:
    """Render the upload flow and latest ingestion result."""
    st.title("Upload a PDF to Ingest")
    uploaded = st.file_uploader("Choose a PDF", type=["pdf"], accept_multiple_files=False)

    if uploaded is not None:
        with st.spinner("Uploading and triggering ingestion..."):
            path = save_uploaded_pdf(uploaded)
            log_security_event(
                "upload_received",
                source_id=path.name,
                pdf_path=str(path.resolve()),
                size_bytes=path.stat().st_size,
            )
            event_id = asyncio.run(send_rag_ingest_event(path))
            output = wait_for_run_output(event_id)
            st.session_state.latest_ingestion_output = {
                "source_id": path.name,
                **output,
            }
        st.success(f"Ingestion finished for: {path.name}")
        st.caption("Latest ingestion result is shown below.")

    latest_ingestion = st.session_state.latest_ingestion_output
    if not latest_ingestion:
        return

    st.subheader("Latest Ingestion Result")
    ingestion_col1, ingestion_col2, ingestion_col3 = st.columns(3)
    ingestion_col1.metric("Decision", latest_ingestion.get("scan_decision", "unknown"))
    ingestion_col2.metric("Chunks ingested", latest_ingestion.get("ingested", 0))
    ingestion_col3.metric("Flags", len(latest_ingestion.get("scan_flags", [])))
    st.caption(f"Source: {latest_ingestion.get('source_id', 'unknown')}")
    if latest_ingestion.get("message"):
        st.write(latest_ingestion["message"])
    if latest_ingestion.get("scan_flags"):
        st.write("Scan flags:")
        for flag in latest_ingestion["scan_flags"]:
            st.write(f"- {flag}")
