"""Remove common personal identifiers before text can enter a reviewed training draft.

Pattern matching is a safety net, not a guarantee; moderators still review the full text.
"""
import re

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def sanitize_for_training(text: str | None) -> str:
    sanitized = EMAIL_RE.sub("[REDACTED_EMAIL]", text or "")
    sanitized = PHONE_RE.sub("[REDACTED_PHONE]", sanitized)
    sanitized = SSN_RE.sub("[REDACTED_SSN]", sanitized)
    return sanitized


def contains_identifiers(*values: str | None) -> bool:
    return any(sanitize_for_training(value) != (value or "") for value in values)
