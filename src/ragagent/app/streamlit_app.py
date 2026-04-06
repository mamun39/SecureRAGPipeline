"""Streamlit interface for the RAG application."""

from dotenv import load_dotenv
import streamlit as st

from ragagent.app.ui.audit_panel import render_audit_panel
from ragagent.app.ui.documents_panel import render_documents_panel
from ragagent.app.ui.ingest_panel import render_ingest_panel
from ragagent.app.ui.query_panel import render_query_panel


load_dotenv()

st.set_page_config(page_title="RAG Security Console", page_icon="PDF", layout="wide")
st.session_state.setdefault("latest_ingestion_output", None)
st.session_state.setdefault("latest_query_output", None)

st.title("Security-Aware RAG Console")
st.caption(
    "Inspect ingestion decisions, retrieval policy behavior, safe-context filtering, "
    "document metadata, and recent audit events in one place."
)

top_col1, top_col2 = st.columns([1, 1.4], gap="large")
with top_col1:
    render_ingest_panel()
with top_col2:
    render_query_panel()

bottom_col1, bottom_col2 = st.columns([1.15, 0.85], gap="large")
with bottom_col1:
    render_documents_panel()
with bottom_col2:
    render_audit_panel()
