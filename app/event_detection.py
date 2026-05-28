from __future__ import annotations

import re

EVENT_PATTERNS = (
    re.compile(r"\bjoin\s+us\s+live\b", re.IGNORECASE),
    re.compile(r"\blive\s+(session|event|webinar|presentation|workshop|demo)\b", re.IGNORECASE),
    re.compile(r"\b(webinar|summit|conference|workshop|demo day)\b", re.IGNORECASE),
    re.compile(r"\b(register|sign up|rsvp)\b", re.IGNORECASE),
    re.compile(r"\b(presenting|speaking|keynote)\b", re.IGNORECASE),
    re.compile(r"\b(today|tonight|tomorrow|next\s+\w+)\b", re.IGNORECASE),
    re.compile(
        r"\b\d{1,2}(:\d{2})?\s?(am|pm|a\.m\.|p\.m\.|est|edt|pst|pdt|cst|cdt)\b",
        re.IGNORECASE,
    ),
)


EVENT_CONTEXT_TERMS = (
    "event",
    "live",
    "webinar",
    "presentation",
    "presenting",
    "speaking",
    "session",
    "workshop",
    "summit",
    "conference",
    "register",
    "rsvp",
    "join us",
)

TIME_CONTEXT_TERMS = (
    "today",
    "tonight",
    "tomorrow",
    "next ",
)


def has_possible_event_language(content: str) -> bool:
    """Return true when a LinkedIn post likely mentions a time-sensitive event.

    This is intentionally lightweight and explainable for v0. It should catch obvious
    live sessions, webinars, presentations, registration prompts, and dated/time-bound
    language without pretending to be a calendar parser.
    """
    normalized = " ".join(content.lower().split())
    if not normalized:
        return False

    matched_patterns = [pattern for pattern in EVENT_PATTERNS if pattern.search(normalized)]
    if len(matched_patterns) >= 2:
        return True

    has_event_context = any(term in normalized for term in EVENT_CONTEXT_TERMS)
    has_time_context = any(term in normalized for term in TIME_CONTEXT_TERMS)
    return has_event_context and has_time_context
