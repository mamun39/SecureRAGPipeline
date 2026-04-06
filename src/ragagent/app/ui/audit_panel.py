"""Audit events panel for the Streamlit UI."""

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

    st.caption(f"Showing the most recent {len(events)} security events.")
    for event in events:
        header = f"{event.get('timestamp', '')} | {event.get('event_type', 'unknown')}"
        with st.expander(header, expanded=False):
            st.json(event)
