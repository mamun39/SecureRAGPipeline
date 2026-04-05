"""Minimal screening for generated answers."""

import re

from custom_types import OutputFilterResult


API_KEY_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
RESTRICTED_LABEL_PATTERN = re.compile(r"\[(?:source=.*?\s)?classification=(confidential|restricted)\s", re.IGNORECASE)


def screen_generated_answer(answer: str) -> OutputFilterResult:
    """Apply small post-generation checks and return an allow/redact/block decision."""
    reasons: list[str] = []

    if any(pattern.search(answer) for pattern in API_KEY_PATTERNS):
        reasons.append("api_key_like_string")

    if RESTRICTED_LABEL_PATTERN.search(answer) and len(answer) > 500:
        reasons.append("restricted_verbatim_dump")

    redact_email = EMAIL_PATTERN.search(answer) is not None
    redact_phone = PHONE_PATTERN.search(answer) is not None
    if redact_email:
        reasons.append("email_like_content")
    if redact_phone:
        reasons.append("phone_like_content")

    if "api_key_like_string" in reasons or "restricted_verbatim_dump" in reasons:
        return OutputFilterResult(
            decision="block",
            filtered_text="Response blocked by output safety filter.",
            reasons=reasons,
        )

    filtered_text = answer
    if redact_email:
        filtered_text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", filtered_text)
    if redact_phone:
        filtered_text = PHONE_PATTERN.sub("[REDACTED_PHONE]", filtered_text)

    if filtered_text != answer:
        return OutputFilterResult(
            decision="redact",
            filtered_text=filtered_text,
            reasons=reasons,
        )

    return OutputFilterResult(
        decision="allow",
        filtered_text=answer,
        reasons=reasons,
    )
