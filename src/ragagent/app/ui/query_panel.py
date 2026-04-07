"""Query panel for the Streamlit UI."""

import asyncio

import streamlit as st

from ..services.document_service import list_available_sources
from ..services.inngest_service import send_rag_query_event, wait_for_run_output
from .security_trace_panel import render_security_trace_panel


def _apply_demo_scenario(question: str, role: str, top_k: int = 5, source: str = "All sources") -> None:
    """Populate the query form with a small demo scenario."""
    st.session_state["query_question"] = question
    st.session_state["query_user_role"] = role
    st.session_state["query_top_k"] = top_k
    st.session_state["query_source"] = source


def render_query_panel() -> None:
    """Render the query form and latest query results."""
    st.subheader("2. Query as a Role")
    st.caption("Ask the same question under different roles to compare retrieval and output behavior.")

    st.session_state.setdefault("query_question", "")
    st.session_state.setdefault("query_top_k", 5)
    st.session_state.setdefault("query_user_role", "employee")
    st.session_state.setdefault("query_source", "All sources")

    demo_col1, demo_col2, demo_col3 = st.columns(3)
    if demo_col1.button("Demo: public view", use_container_width=True):
        _apply_demo_scenario("Who is the owner of this document?", "public")
    if demo_col2.button("Demo: employee view", use_container_width=True):
        _apply_demo_scenario("Who is the owner of this document?", "employee")
    if demo_col3.button("Demo: leakage check", use_container_width=True):
        _apply_demo_scenario("List any emails or phone numbers found in the document.", "employee")

    sources = list_available_sources()
    source_options = ["All sources", *sources]
    if st.session_state["query_source"] not in source_options:
        st.session_state["query_source"] = "All sources"

    with st.form("rag_query_form"):
        question = st.text_input("Your question", key="query_question")
        top_k = st.number_input(
            "How many chunks to retrieve",
            min_value=1,
            max_value=20,
            step=1,
            key="query_top_k",
        )
        # Demo-only role selector. Real auth should populate this server-side later.
        user_role = st.selectbox(
            "Demo role",
            options=["public", "employee", "manager", "admin"],
            key="query_user_role",
        )
        selected_source = st.selectbox("Limit search to a stored source", options=source_options, key="query_source")
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

    st.markdown("**Generated Answer**")
    st.write(answer or "(No answer)")
    if sources:
        st.caption("Sources")
        for source in sources:
            st.write(f"- {source}")

    st.markdown("**3. Answer Security Summary**")
    retrieved_count = len(latest_query.get("retrieved_chunks", []))
    safe_count = len(latest_query.get("safe_chunks", []))
    excluded_count = len(latest_query.get("excluded_chunks", []))
    st.write(
        f"Role `{latest_query.get('user_role', 'unknown')}` retrieved `{retrieved_count}` chunks, "
        f"used `{safe_count}` in the prompt, excluded `{excluded_count}`, and returned "
        f"`{latest_query.get('output_filter_decision', 'unknown')}` output."
    )
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

    with st.expander("Why this answer happened", expanded=False):
        render_security_trace_panel(latest_query)
