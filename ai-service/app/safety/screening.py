"""Conservative first-pass checks for urgent and personal medical requests."""

import re


URGENT_PERSONAL_PATTERN = re.compile(
    r"\b(?:i am|i'm|i have|my|someone is|right now|currently)\b.{0,100}"
    r"\b(?:chest pain|trouble breathing|difficulty breathing|unconscious|"
    r"severe bleeding|overdose|stroke symptoms)\b",
    re.IGNORECASE,
)

PERSONAL_DECISION_PATTERNS = (
    re.compile(r"\b(?:diagnose me|do i have|what's wrong with me)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:should|can|could|may) i\b.{0,50}\b(?:take|stop|change|increase|decrease)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bwhat (?:dose|dosage) should i\b", re.IGNORECASE),
    re.compile(r"\bmy (?:symptoms|medication|prescription)\b", re.IGNORECASE),
)


def safety_message(question: str) -> str | None:
    """Return a safety boundary for obvious high-risk wording, otherwise None."""
    if URGENT_PERSONAL_PATTERN.search(question):
        return (
            "This may describe an urgent situation. MediScope cannot assess emergencies; "
            "contact your local emergency service or a medical professional now."
        )
    if any(pattern.search(question) for pattern in PERSONAL_DECISION_PATTERNS):
        return (
            "MediScope cannot diagnose you or recommend personal treatment or medication "
            "changes. Please contact a qualified healthcare professional."
        )
    return None
