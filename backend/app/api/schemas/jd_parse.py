from typing import Literal

from pydantic import BaseModel, Field

Seniority = Literal["junior", "mid", "senior", "staff"]
SalaryConfidence = Literal["stated", "estimated", "unknown"]


class ParseJDRequest(BaseModel):
    jd_text: str = Field(min_length=1)


class ParsedJobDescription(BaseModel):
    """Structured extraction from a raw job posting.

    Doubles as both the API response shape and the LLM's forced
    structured-output target — one schema, no separate DTO to keep in sync.

    Every field is required, even when its value can be null or an empty list:
    JSON-mode/tool-use structured output is much more reliable when the model must
    always fill every key, rather than being allowed to omit fields it's unsure about.
    """

    required_skills: list[str]
    nice_to_have_skills: list[str]

    seniority_claimed: str | None = Field(
        description=(
            "Seniority implied by the job title itself (e.g. 'Senior' in "
            "'Senior AI Engineer'), or null if the title carries no level"
        )
    )
    seniority_assessed: Seniority = Field(
        description=(
            "Actual seniority implied by the requirements and responsibilities, "
            "independent of the title"
        )
    )

    tech_stack: list[str]
    languages: list[str] = Field(
        description="Spoken/written languages required, e.g. 'German', 'English'"
    )
    years_experience_min: int | None
    remote_policy: str | None
    salary_range: str | None
    salary_confidence: SalaryConfidence

    key_responsibilities: list[str]
    red_flags: list[str]
    missing_info: list[str] = Field(
        description="Standard posting details missing entirely, e.g. 'no salary range'"
    )
    summary: str = Field(description="One-sentence summary of the role")
