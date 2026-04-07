"""Streamlit interface for the RAG application."""

from dotenv import load_dotenv
import streamlit as st

from ragagent.app.ui.audit_panel import render_audit_panel
from ragagent.app.ui.documents_panel import render_documents_panel
from ragagent.app.ui.ingest_panel import render_ingest_panel
from ragagent.app.ui.query_panel import render_query_panel
from ragagent.app.services.document_service import load_document_summaries


load_dotenv()

st.set_page_config(page_title="RAG Security Console", page_icon="PDF", layout="wide")
st.session_state.setdefault("latest_ingestion_output", None)
st.session_state.setdefault("latest_query_output", None)

st.title("Security-Aware RAG Console")
st.caption(
    "Inspect ingestion decisions, retrieval policy behavior, safe-context filtering, "
    "document metadata, and recent audit events in one place."
)

documents, _document_error = load_document_summaries()
latest_ingestion = st.session_state.latest_ingestion_output or {}
latest_query = st.session_state.latest_query_output or {}

summary_col1, summary_col2, summary_col3 = st.columns(3)
summary_col1.metric("Documents stored", len(documents))
summary_col2.metric("Last ingest decision", latest_ingestion.get("scan_decision", "none"))
summary_col3.metric("Last query role", latest_query.get("user_role", "none"))

with st.expander("How to use this demo", expanded=False):
    st.write("1. Upload a PDF and choose its classification and trust level.")
    st.write("2. Ask the same question under different roles to compare retrieval outcomes.")
    st.write("3. Inspect the answer summary, then expand the trace if you want the raw retrieval details.")
    st.write("4. Use the Documents and Audit tabs to inspect stored metadata and logged security events.")

demo_tab, documents_tab, audit_tab, about_tab = st.tabs(["Demo", "Documents", "Audit", "About"])

with demo_tab:
    top_col1, top_col2 = st.columns([1, 1.4], gap="large")
    with top_col1:
        render_ingest_panel()
    with top_col2:
        render_query_panel()

with documents_tab:
    render_documents_panel()

with audit_tab:
    render_audit_panel()

with about_tab:
    st.subheader("About This Demo")
    st.caption("Use this tab as a quick orientation guide before exploring the detailed traces.")
    st.write("This app demonstrates layered, app-level security controls around a simple RAG pipeline.")
    st.write("Key controls shown in the UI:")
    st.write("- Ingestion-time scanning with allow, review, and quarantine decisions")
    st.write("- Retrieval-time access filtering based on demo role and document classification")
    st.write("- Safe context construction before the LLM call")
    st.write("- Output screening after generation")
    st.write("- Structured audit logging")
    st.write("Role access mapping:")
    st.write("- public -> public")
    st.write("- employee -> public, internal")
    st.write("- manager -> public, internal, confidential")
    st.write("- admin -> public, internal, confidential, restricted")
