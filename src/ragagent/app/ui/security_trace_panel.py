"""Security trace panel for the Streamlit UI."""

import streamlit as st


def render_security_trace_panel(latest_query: dict) -> None:
    """Render the retrieval trace for the latest query result."""
    st.markdown("**Security Trace**")
    st.caption("Trace what was retrieved, what was kept for context, and what was excluded.")
    retrieved_chunks = latest_query.get("retrieved_chunks", [])
    safe_chunks = latest_query.get("safe_chunks", [])
    excluded_chunks = latest_query.get("excluded_chunks", [])

    trace_col1, trace_col2, trace_col3 = st.columns(3)
    trace_col1.metric("Retrieved", len(retrieved_chunks))
    trace_col2.metric("Kept", len(safe_chunks))
    trace_col3.metric("Excluded", len(excluded_chunks))

    if retrieved_chunks:
        with st.expander("Retrieved chunks", expanded=False):
            for idx, chunk in enumerate(retrieved_chunks, start=1):
                st.write(
                    f"{idx}. source={chunk.get('source', '')} "
                    f"classification={chunk.get('classification', '')} "
                    f"trust={chunk.get('trust_level', '')}"
                )
                st.caption(chunk.get("text_preview", ""))

    if safe_chunks:
        with st.expander("Safe chunks kept", expanded=False):
            for idx, chunk in enumerate(safe_chunks, start=1):
                st.write(
                    f"{idx}. source={chunk.get('source', '')} "
                    f"classification={chunk.get('classification', '')} "
                    f"trust={chunk.get('trust_level', '')}"
                )
                st.caption(chunk.get("text_preview", ""))

    if excluded_chunks:
        with st.expander("Excluded chunks", expanded=False):
            for idx, chunk in enumerate(excluded_chunks, start=1):
                st.write(
                    f"{idx}. source={chunk.get('source', '')} "
                    f"classification={chunk.get('classification', '')} "
                    f"trust={chunk.get('trust_level', '')} "
                    f"reason={chunk.get('exclusion_reason', 'unknown')}"
                )
                st.caption(chunk.get("text_preview", ""))
