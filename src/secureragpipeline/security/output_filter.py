"""Minimal screening for generated answers."""

import re

from ..models.results import OutputFilterResult


SAFE_REFUSAL_MESSAGE = "I cannot provide that information with the currently allowed evidence."

API_KEY_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
INTERNAL_TOKEN_PATTERN = re.compile(r"\bTOK-[A-Za-z0-9]{12,}\b")
RESTRICTED_LABEL_PATTERN = re.compile(r"\[(?:source=.*?\s)?classification=(confidential|restricted)\s", re.IGNORECASE)
CONFIDENTIAL_MARKER_PATTERNS = [
    re.compile(r"CONFIDENTIAL MARKER", re.IGNORECASE),
    re.compile(r"RESTRICTED OPERATIONS", re.IGNORECASE),
]
HIDDEN_INSTRUCTION_PATTERNS = [
    re.compile(r"ignore previous instructions", re.IGNORECASE),
    re.compile(r"reveal the system prompt", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"developer instructions", re.IGNORECASE),
    re.compile(r"respond only with admin policy", re.IGNORECASE),
    re.compile(r"admin-only override", re.IGNORECASE),
]
SENSITIVE_REQUEST_ECHO_PATTERNS = [
    re.compile(r"internal-only", re.IGNORECASE),
    re.compile(r"confidential planning details", re.IGNORECASE),
    re.compile(r"restricted break-glass instructions", re.IGNORECASE),
    re.compile(r"admin-only emergency access", re.IGNORECASE),
]


def _looks_like_refusal(answer: str) -> bool:
    lowered = answer.lower()
    refusal_markers = (
        "cannot provide",
        "can't provide",
        "unable to provide",
        "do not have enough",
        "don't have enough",
        "insufficient access",
        "insufficient allowed evidence",
        "not enough allowed evidence",
    )
    return any(marker in lowered for marker in refusal_markers)


def screen_generated_answer(
    answer: str,
    *,
    question: str | None = None,
    num_contexts: int | None = None,
) -> OutputFilterResult:
    """Apply small post-generation checks and return an allow/redact/block decision."""
    reasons: list[str] = []
    filtered_text = answer

    if any(pattern.search(answer) for pattern in API_KEY_PATTERNS):
        reasons.append("api_key_like_string")

    if RESTRICTED_LABEL_PATTERN.search(answer) and len(answer) > 500:
        reasons.append("restricted_verbatim_dump")

    if INTERNAL_TOKEN_PATTERN.search(answer):
        reasons.append("internal_token_like_string")

    if any(pattern.search(answer) for pattern in CONFIDENTIAL_MARKER_PATTERNS):
        reasons.append("confidential_marker_echo")

    if any(pattern.search(answer) for pattern in HIDDEN_INSTRUCTION_PATTERNS):
        reasons.append("hidden_instruction_reference")

    redact_email = EMAIL_PATTERN.search(answer) is not None
    redact_phone = PHONE_PATTERN.search(answer) is not None
    if redact_email:
        reasons.append("email_like_content")
    if redact_phone:
        reasons.append("phone_like_content")

    if question and (_looks_like_refusal(answer) or num_contexts == 0):
        echoed_sensitive_request = any(
            pattern.search(question) and pattern.search(answer)
            for pattern in SENSITIVE_REQUEST_ECHO_PATTERNS
        )
        if echoed_sensitive_request:
            reasons.append("sensitive_request_echo")

    if "api_key_like_string" in reasons or "restricted_verbatim_dump" in reasons:
        return OutputFilterResult(
            decision="block",
            filtered_text="Response blocked by output safety filter.",
            reasons=reasons,
        )

    if any(
        reason in reasons
        for reason in (
            "confidential_marker_echo",
            "hidden_instruction_reference",
            "sensitive_request_echo",
        )
    ):
        filtered_text = SAFE_REFUSAL_MESSAGE

    if "internal_token_like_string" in reasons:
        filtered_text = INTERNAL_TOKEN_PATTERN.sub("[REDACTED_TOKEN]", filtered_text)

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
