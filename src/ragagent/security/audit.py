"""Small helper for structured security event logging."""

import datetime
import json
import logging
import os
from pathlib import Path


def _audit_log_path() -> Path:
    """Return the local JSONL file used for demo audit event sharing."""
    return Path(os.getenv("RAG_AUDIT_LOG_PATH", "audit_events.jsonl"))


def log_security_event(event_type: str, **fields) -> None:
    """Emit a compact JSON-style security log event."""
    logger = logging.getLogger("uvicorn")
    payload = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "event_type": event_type,
        **fields,
    }
    serialized = json.dumps(payload, sort_keys=True, default=str)
    logger.info(serialized)
    try:
        with _audit_log_path().open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
    except OSError:
        logger.warning("Failed to append security event to local audit log file.")


def read_recent_security_events(limit: int = 50) -> list[dict]:
    """Read the most recent security events from the local JSONL audit file."""
    path = _audit_log_path()
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()[-limit:]

    events: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(events))
