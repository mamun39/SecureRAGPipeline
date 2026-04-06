"""Streamlit interface for the RAG application."""

import asyncio
import os
from pathlib import Path
import time

from dotenv import load_dotenv
import inngest
import requests
import streamlit as st

from ragagent.security.audit import log_security_event


load_dotenv()

st.set_page_config(page_title="RAG Ingest PDF", page_icon="ðŸ“„", layout="centered")


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    """Create and cache the Inngest client used by the Streamlit app."""
    return inngest.Inngest(app_id="rag_app", is_production=False)


def save_uploaded_pdf(file) -> Path:
    """Save an uploaded PDF to disk and return its local path."""
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())
    return file_path


def list_available_sources() -> list[str]:
    """Return currently available source IDs for UI filtering."""
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        return []
    return sorted({path.name for path in uploads_dir.glob("*.pdf") if path.is_file()})


async def send_rag_ingest_event(pdf_path: Path) -> None:
    """Send an event telling the backend to ingest the saved PDF."""
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name,
            },
        )
    )


async def send_rag_query_event(
    question: str,
    top_k: int,
    source_id: str | None = None,
    user_role: str = "employee",
) -> None:
    """Send a question event and return the created Inngest event ID."""
    client = get_inngest_client()
    event_data = {
        "question": question,
        "top_k": top_k,
        "user_role": user_role,
    }
    if source_id:
        event_data["source_id"] = source_id

    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data=event_data,
        )
    )
    return result[0]


def _inngest_api_base() -> str:
    """Return the base URL for the local Inngest development API."""
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


def fetch_runs(event_id: str) -> list[dict]:
    """Fetch workflow runs associated with a previously sent event."""
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    """Poll Inngest until the run finishes and then return its output."""
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)


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
        asyncio.run(send_rag_ingest_event(path))
        time.sleep(0.3)
    st.success(f"Triggered ingestion for: {path.name}")
    st.caption("You can upload another PDF if you like.")

st.divider()
st.title("Ask a question about your PDFs")

with st.form("rag_query_form"):
    question = st.text_input("Your question")
    top_k = st.number_input("How many chunks to retrieve", min_value=1, max_value=20, value=5, step=1)
    # Demo-only role selector. Real auth should populate this server-side later.
    user_role = st.selectbox("Demo role", options=["public", "employee", "manager", "admin"], index=1)
    sources = list_available_sources()
    source_options = ["All sources", *sources]
    selected_source = st.selectbox("Limit search to a source", options=source_options, index=0)
    submitted = st.form_submit_button("Ask")

    if submitted and question.strip():
        with st.spinner("Sending event and generating answer..."):
            source_filter = None if selected_source == "All sources" else selected_source
            event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k), source_filter, user_role))
            output = wait_for_run_output(event_id)
            answer = output.get("answer", "")
            sources = output.get("sources", [])

        st.subheader("Answer")
        st.write(answer or "(No answer)")
        if sources:
            st.caption("Sources")
            for source in sources:
                st.write(f"- {source}")
