"""
Thread Cleaner: Extracts clean summary from raw ticket description.
Removes email threading artifacts (>, -----Original-----, etc.)
"""

import re


def extract_clean_summary(description: str, max_length: int = 200) -> str:
    """
    Strip email thread markers and extract first meaningful sentence(s).
    """
    if not description:
        return ""

    text = _remove_thread_artifacts(description)
    text = _collapse_whitespace(text)
    text = text.strip()

    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.6:
        truncated = truncated[:last_space]

    return truncated + "..."


def _remove_thread_artifacts(text: str) -> str:
    patterns = [
        r"-+original\s*message-+\s*",
        r"-{5,}\s*from\s+.+-{5,}\s*",
        r"from:\s+.+",
        r"sent:\s+.+",
        r"to:\s+.+",
        r"subject:\s*.+",
        r"-+ forwarded\s*by.+-{5,}\s*",
        r"_{10,}\s*",
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r">\s*", " ", text)
    text = re.sub(r"^[^a-zA-Z]*>", "", text, flags=re.MULTILINE)

    return text


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def clean_text(raw: str) -> str:
    """Strip noise from titles and body text."""
    if not raw:
        return ""

    cleaned = re.sub(r"TICKET #\d+: ", "", raw)
    cleaned = re.sub(r" HAS BEEN UPDATED$", "", cleaned)
    cleaned = re.sub(r" IS RESOLVED AND CLOSED$", "", cleaned)
    cleaned = re.sub(r"^(Fw:|Fwd:)\s*", "", cleaned)
    cleaned = re.sub(r"Ticket#\d+/Company/\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_status(raw: str) -> str:
    """Normalize status values, handle data errors."""
    if not raw:
        return "Open"

    if "@" in raw:
        return "In Progress"

    status_map = {
        "closed": "Closed",
        "resolved": "Resolved",
        "in progress": "In Progress",
        "in-progress": "In Progress",
        "waiting": "Waiting Info",
        "waiting for info": "Waiting Info",
        "open": "Open",
    }
    return status_map.get(raw.strip().lower(), raw.strip())


def normalize_priority(raw: str) -> str:
    """Normalize priority values."""
    if not raw:
        return "Medium"

    priority_map = {
        "critical": "Critical",
        "crit": "Critical",
        "high": "High",
        "hi": "High",
        "medium": "Medium",
        "med": "Medium",
        "low": "Low",
    }
    return priority_map.get(raw.strip().lower(), raw.strip())


def clean_assignee(raw: str | None) -> str:
    """Normalize assignee field, handle None/empty."""
    if not raw:
        return "Unassigned"

    normalized = raw.strip().lower()
    if normalized in ("n/a", "none", "unassigned", ""):
        return "Unassigned"
    return raw.strip()


def clean_site_id(raw: str | None) -> str:
    """Normalize site_id field."""
    if not raw:
        return "—"
    return raw.strip()


def normalize_category(raw: str | None) -> str:
    """Normalize category/request_type field."""
    if not raw:
        return "—"
    cleaned = raw.strip()
    return cleaned if cleaned else "—"
