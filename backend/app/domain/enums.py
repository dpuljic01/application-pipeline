from __future__ import annotations

from enum import Enum


class ApplicationStage(str, Enum):
    SAVED = "SAVED"
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


ALLOWED_TRANSITIONS: dict[ApplicationStage, set[ApplicationStage]] = {
    ApplicationStage.SAVED: {ApplicationStage.APPLIED, ApplicationStage.WITHDRAWN},
    ApplicationStage.APPLIED: {
        ApplicationStage.INTERVIEW,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
    },
    ApplicationStage.INTERVIEW: {
        ApplicationStage.OFFER,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
    },
    ApplicationStage.OFFER: {ApplicationStage.REJECTED, ApplicationStage.WITHDRAWN},
    ApplicationStage.REJECTED: set(),
    ApplicationStage.WITHDRAWN: set(),
}


class ActivityType(str, Enum):
    NOTE = "NOTE"
    OUTREACH = "OUTREACH"
    FOLLOW_UP = "FOLLOW_UP"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTION = "REJECTION"
