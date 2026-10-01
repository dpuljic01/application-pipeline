from __future__ import annotations

from enum import Enum


class ApplicationStage(str, Enum):
    SAVED = "SAVED"
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    GHOSTED = "GHOSTED"


ALLOWED_TRANSITIONS: dict[ApplicationStage, set[ApplicationStage]] = {
    ApplicationStage.SAVED: {ApplicationStage.APPLIED, ApplicationStage.WITHDRAWN},
    ApplicationStage.APPLIED: {
        ApplicationStage.INTERVIEW,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
        ApplicationStage.GHOSTED,
    },
    ApplicationStage.INTERVIEW: {
        ApplicationStage.OFFER,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
        ApplicationStage.GHOSTED,
    },
    ApplicationStage.OFFER: {
        ApplicationStage.ACCEPTED,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
    },
    ApplicationStage.REJECTED: set(),
    ApplicationStage.WITHDRAWN: set(),
    ApplicationStage.ACCEPTED: set(),
    ApplicationStage.GHOSTED: set(),
}


class ActivityType(str, Enum):
    ACCEPTED = "ACCEPTED"
    GHOSTED = "GHOSTED"
    NOTE = "NOTE"
    OUTREACH = "OUTREACH"
    FOLLOW_UP = "FOLLOW_UP"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTION = "REJECTION"
    STAGE_CHANGE = "STAGE_CHANGE"


class PipelineStatus(str, Enum):
    """State of the automatic parse -> score run started on application
    creation. COMPLETED/FAILED are terminal; FAILED keeps whatever earlier
    steps already saved (e.g. parsed_jd survives a scoring failure)."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LLMProviderName(str, Enum):
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class CompanySize(str, Enum):
    STARTUP = "STARTUP"
    MID = "MID"
    ENTERPRISE = "ENTERPRISE"
