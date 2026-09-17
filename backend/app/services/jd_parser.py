from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.domain.errors import JDParseError
from app.integrations.llm.base import LLMProvider, LLMProviderError, LLMTimeoutError

# Lives here, not in api/schemas/: this is the LLM's forced structured-output
# target and matcher.py's business-logic input, not just an API response
# shape. It happens to double as one (see api/schemas/application.py), but
# services shouldn't have to reach into the API layer to get their own
# domain data - api/schemas imports FROM here, not the other way around.
Seniority = Literal["junior", "mid", "senior", "staff"]
SalaryConfidence = Literal["stated", "estimated", "unknown"]


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


SYSTEM_PROMPT = """\
You are an expert technical recruiter analyzing job postings for the Swiss/DACH
market. Extract structured data from the job description below.

Be conservative: only extract what's explicitly stated or clearly implied. Use
null or an empty list when something is genuinely absent — never invent
information.

Distinguish the seniority implied by the job TITLE from the seniority implied
by the actual REQUIREMENTS — these often disagree (title inflation).

German language requirements need judgment, not a literal reading: "fliessend"
or "verhandlungssicher" German stated as a hard requirement is a real
must-have — flag it as a red flag. "Sehr gute" or "gute Deutschkenntnisse" is
frequently overstated in Swiss/DACH postings, and teams often function fine in
English — do not flag this on its own.

Other red flags: missing salary range, vague work-permit requirements, unpaid
trial periods, and requirements mismatched with the stated seniority.

`languages` lists only spoken/written language requirements — do not duplicate
them into `required_skills`.
"""


def parse_job_description(llm: LLMProvider, *, jd_text: str) -> ParsedJobDescription:
    try:
        response = llm.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=jd_text,
            response_schema=ParsedJobDescription,
        )
    except (LLMProviderError, LLMTimeoutError) as exc:
        raise JDParseError(f"LLM call failed: {exc}") from exc

    try:
        return ParsedJobDescription.model_validate_json(response.content)
    except ValidationError as exc:
        raise JDParseError(f"LLM returned invalid structured output: {exc}") from exc
