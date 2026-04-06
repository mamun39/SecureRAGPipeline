"""Query panel for the Streamlit UI."""

import asyncio

import streamlit as st

from ..services.document_service import list_available_sources
from ..services.inngest_service import send_rag_query_event, wait_for_run_output
from .security_trace_panel import render_security_trace_panel


def render_query_panel() -> None:
    """Render the query form and latest query results."""
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
                st.session_state.latest_query_output = wait_for_run_output(event_id)

    latest_query = st.session_state.latest_query_output
    if not latest_query:
        return

    answer = latest_query.get("answer", "")
    sources = latest_query.get("sources", [])

    st.subheader("Answer")
    st.write(answer or "(No answer)")
    if sources:
        st.caption("Sources")
        for source in sources:
            st.write(f"- {source}")

    st.subheader("Query Security State")
    query_col1, query_col2, query_col3 = st.columns(3)
    query_col1.metric("Role", latest_query.get("user_role", "unknown"))
    query_col2.metric("Allowed classifications", len(latest_query.get("allowed_classifications", [])))
    query_col3.metric("Safe contexts", latest_query.get("num_contexts", 0))
    allowed_classifications = latest_query.get("allowed_classifications", [])
    st.write(
        "Allowed classifications: " + ", ".join(allowed_classifications)
        if allowed_classifications
        else "Allowed classifications: none"
    )
    st.write(f"Output filter decision: {latest_query.get('output_filter_decision', 'unknown')}")
    if latest_query.get("output_filter_reasons"):
        st.write("Output filter reasons:")
        for reason in latest_query["output_filter_reasons"]:
            st.write(f"- {reason}")

    render_security_trace_panel(latest_query)
