"""Basic ingestion-time scanning for suspicious document content."""

from ..models.results import IngestScanResult


SUSPICIOUS_PHRASES = [
    "ignore previous instructions",
    "reveal system prompt",
    "exfiltrate",
    "system prompt",
    "execute",
]


def scan_document_text(text: str) -> IngestScanResult:
    """Scan extracted document text and return a lightweight risk result."""
    normalized_text = text.lower()
    flags: list[str] = []

    for phrase in SUSPICIOUS_PHRASES:
        if phrase in normalized_text:
            flags.append(phrase)

    score = len(flags)
    if score >= 3:
        decision = "quarantine"
    elif score >= 1:
        decision = "review"
    else:
        decision = "allow"

    return IngestScanResult(score=score, flags=flags, decision=decision)
