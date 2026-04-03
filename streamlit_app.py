"""Simple Streamlit interface for the RAG application.

This file gives the user a small web UI for two tasks:

1. Upload a PDF so it can be ingested into the vector database.
2. Ask a question that will be answered using the ingested PDFs.

The important idea is that this UI does not do the heavy backend work itself.
Instead, it sends events to Inngest, and the backend functions handle the
actual ingestion and question-answering workflow.
"""

import asyncio
from pathlib import Path
import time

import streamlit as st
import inngest
from dotenv import load_dotenv
import os
import requests

# Load local environment variables before creating clients or reading settings.
load_dotenv()

st.set_page_config(page_title="RAG Ingest PDF", page_icon="📄", layout="centered")


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    """Create and cache the Inngest client used by the Streamlit app.

    Streamlit reruns this script whenever the user interacts with the page.
    Caching prevents the client from being recreated each time.
    """
    return inngest.Inngest(app_id="rag_app", is_production=False)


def save_uploaded_pdf(file) -> Path:
    """Save an uploaded PDF to disk and return its local path.

    The backend ingestion workflow expects a real file path, so the uploaded
    file must be written to disk before sending the event.
    """
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_bytes = file.getbuffer()
    file_path.write_bytes(file_bytes)
    return file_path


def list_available_sources() -> list[str]:
    """Return currently available source IDs for UI filtering.

    For now we use local uploaded PDF names as source IDs because ingestion
    stores `source_id` as the uploaded filename.
    """
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        return []
    return sorted({p.name for p in uploads_dir.glob("*.pdf") if p.is_file()})


async def send_rag_ingest_event(pdf_path: Path) -> None:
    """Send an event telling the backend to ingest the saved PDF.

    The backend function will later read the file, split it into chunks,
    create embeddings, and store those embeddings in Qdrant.
    """
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


st.title("Upload a PDF to Ingest")
uploaded = st.file_uploader("Choose a PDF", type=["pdf"], accept_multiple_files=False)

if uploaded is not None:
    with st.spinner("Uploading and triggering ingestion..."):
        # Save the uploaded file locally so the backend can read it from disk.
        path = save_uploaded_pdf(uploaded)
        # Send the ingestion event and wait until the event submission completes.
        asyncio.run(send_rag_ingest_event(path))
        # Short delay to make the UI transition feel smoother.
        time.sleep(0.3)
    st.success(f"Triggered ingestion for: {path.name}")
    st.caption("You can upload another PDF if you like.")

st.divider()
st.title("Ask a question about your PDFs")


async def send_rag_query_event(question: str, top_k: int, source_id: str | None = None) -> None:
    """Send a question event and return the created Inngest event ID.

    The returned event ID is important because it lets the UI ask Inngest
    about the status and final output of the workflow run.
    """
    client = get_inngest_client()
    event_data = {
        "question": question,
        "top_k": top_k,
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
    # Local dev server default; configurable via env
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


def fetch_runs(event_id: str) -> list[dict]:
    """Fetch workflow runs associated with a previously sent event.

    One sent event can create one or more runs. In this app, we read the
    first run and use it to inspect status and output.
    """
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    """Poll Inngest until the run finishes and then return its output.

    This function repeatedly checks the run status until one of three things
    happens:
    - the run succeeds, so we return its output
    - the run fails, so we raise an error
    - the timeout is reached, so we stop waiting
    """
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


with st.form("rag_query_form"):
    question = st.text_input("Your question")
    top_k = st.number_input("How many chunks to retrieve", min_value=1, max_value=20, value=5, step=1)
    sources = list_available_sources()
    source_options = ["All sources", *sources]
    selected_source = st.selectbox("Limit search to a source", options=source_options, index=0)
    submitted = st.form_submit_button("Ask")

    if submitted and question.strip():
        with st.spinner("Sending event and generating answer..."):
            source_filter = None if selected_source == "All sources" else selected_source
            # Send the question as an event so the backend workflow can handle it.
            event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k), source_filter))
            # Poll the local Inngest API until the workflow returns an output.
            output = wait_for_run_output(event_id)
            answer = output.get("answer", "")
            sources = output.get("sources", [])

        st.subheader("Answer")
        st.write(answer or "(No answer)")
        if sources:
            st.caption("Sources")
            for s in sources:
                st.write(f"- {s}")
