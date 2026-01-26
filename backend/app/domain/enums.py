from enum import Enum

class ApplicationStage(str, Enum):
    SAVED = "SAVED"
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"

class ActivityType(str, Enum):
    NOTE = "NOTE"
    OUTREACH = "OUTREACH"
    FOLLOW_UP = "FOLLOW_UP"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTION = "REJECTION"
