"""Inngest-facing helpers used by the Streamlit UI."""

import os
import time
from pathlib import Path

import inngest
import requests
import streamlit as st


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    """Create and cache the Inngest client used by the Streamlit app."""
    return inngest.Inngest(app_id="rag_app", is_production=False)


async def send_rag_ingest_event(
    pdf_path: Path,
    classification: str = "internal",
    trust_level: str = "user_uploaded",
) -> str:
    """Send an event telling the backend to ingest the saved PDF."""
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name,
                "classification": classification,
                "trust_level": trust_level,
            },
        )
    )
    return result[0]


async def send_rag_query_event(
    question: str,
    top_k: int,
    source_id: str | None = None,
    user_role: str = "employee",
) -> str:
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
