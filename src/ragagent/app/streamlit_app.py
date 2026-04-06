"""Streamlit interface for the RAG application."""

from dotenv import load_dotenv
import streamlit as st

from ragagent.app.ui.documents_panel import render_documents_panel
from ragagent.app.ui.ingest_panel import render_ingest_panel
from ragagent.app.ui.query_panel import render_query_panel


load_dotenv()

st.set_page_config(page_title="RAG Ingest PDF", page_icon="PDF", layout="centered")
st.session_state.setdefault("latest_ingestion_output", None)
st.session_state.setdefault("latest_query_output", None)
render_ingest_panel()
render_query_panel()

render_documents_panel()
