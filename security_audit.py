"""Small helper for structured security event logging."""

import json
import logging


def log_security_event(event_type: str, **fields) -> None:
    """Emit a compact JSON-style security log event."""
    logger = logging.getLogger("uvicorn")
    payload = {
        "event_type": event_type,
        **fields,
    }
    logger.info(json.dumps(payload, sort_keys=True, default=str))
