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


class LLMProviderName(str, Enum):
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    CEREBRAS = "cerebras"


class CompanySize(str, Enum):
    STARTUP = "STARTUP"
    MID = "MID"
    ENTERPRISE = "ENTERPRISE"
