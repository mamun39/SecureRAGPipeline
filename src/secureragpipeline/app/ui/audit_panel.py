"""Audit events panel for the Streamlit UI."""

from collections import Counter

import streamlit as st

from ...security.audit import read_recent_security_events


def render_audit_panel(limit: int = 20) -> None:
    """Render recent structured security events from the local audit log."""
    st.subheader("Audit Events")
    st.caption("Recent structured security events emitted by the demo pipeline.")

    events = read_recent_security_events(limit=limit)
    if not events:
        st.caption("No audit events found yet.")
        return

    event_types = sorted({event.get("event_type", "unknown") for event in events})

    filter_col1, filter_col2 = st.columns(2)
    source_query = filter_col1.text_input("Search source/doc", key="audit_source_query").strip().lower()
    selected_event_types = filter_col2.multiselect(
        "Event type",
        options=event_types,
        default=event_types,
        key="audit_event_type_filter",
    )

    filtered_events = [
        event
        for event in events
        if event.get("event_type", "unknown") in selected_event_types
        and (
            not source_query
            or source_query in str(event.get("source_id", "")).lower()
            or source_query in str(event.get("doc_id", "")).lower()
            or source_query in str(event.get("source", "")).lower()
        )
    ]

    st.caption(f"Showing {len(filtered_events)} of the most recent {len(events)} security events.")
    if not filtered_events:
        st.caption("No audit events match the current filters.")
        return

    event_counts = Counter(event.get("event_type", "unknown") for event in filtered_events)
    st.markdown("**Event Summary**")
    summary_columns = st.columns(min(4, max(1, len(event_counts))))
    for idx, (event_type, count) in enumerate(event_counts.most_common(4)):
        summary_columns[idx].metric(event_type, count)

    for event in filtered_events:
        source_label = (
            event.get("source_id")
            or event.get("doc_id")
            or event.get("source")
            or "no source"
        )
        header = (
            f"{event.get('timestamp', '')} | "
            f"{event.get('event_type', 'unknown')} | "
            f"{source_label}"
        )
        with st.expander(header, expanded=False):
            st.json(event)
