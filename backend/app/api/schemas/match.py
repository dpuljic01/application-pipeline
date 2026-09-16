from pydantic import BaseModel, Field


class MatchInsights(BaseModel):
    """LLM-generated qualitative read of fit, alongside the deterministic
    rule-based score - see services/matcher.py. Never changes the numeric
    match_score itself."""

    fit_narrative: str = Field(
        description="2-4 sentence honest assessment of fit, including gaps"
    )
    key_strengths: list[str]
    gaps: list[str]
    talking_points: list[str] = Field(
        description="Cover-letter-ready points connecting the candidate's profile to this specific role"
    )
