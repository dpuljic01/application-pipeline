import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.db.repositories.llm_cache_repo import LLMCacheRepository
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


# Shared with services/cv_extractor.py. The matcher compares skills by exact
# (lowercased) string, so a CV saying "Postgres" and a posting saying
# "PostgreSQL" would otherwise never match - both extractions are told to
# emit the same canonical names.
SKILL_NAMING_RULES = """\
Skill names: use the most common canonical name for each skill, one skill
per entry - e.g. "PostgreSQL" not "Postgres"/"psql", "Kubernetes" not "k8s",
"JavaScript" not "JS", "AWS" for Amazon Web Services in general but keep
specific services separate ("AWS Lambda"). No versions ("Python", not
"Python 3.11"), no proficiency words ("Docker", not "Docker (advanced)").
"""

SYSTEM_PROMPT = (
    """\
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
    + SKILL_NAMING_RULES
)


# Derived from the prompt and output schema rather than a hand-bumped
# constant: any edit to either changes the version, so a stale cached parse
# can never be served for a prompt that would now answer differently.
PROMPT_VERSION = hashlib.sha256(
    (
        SYSTEM_PROMPT
        + json.dumps(ParsedJobDescription.model_json_schema(), sort_keys=True)
    ).encode()
).hexdigest()[:12]

CACHE_OPERATION = "parse_jd"


def _validate_output(response_content: str) -> tuple[ParsedJobDescription | None, str]:
    """Returns (parsed, "") on success, (None, reason) when the output fails
    either the schema or the one semantic check worth retrying for."""
    try:
        parsed = ParsedJobDescription.model_validate_json(response_content)
    except ValidationError as exc:
        return (
            None,
            f"it did not match the required schema ({exc.error_count()} errors)",
        )
    if not parsed.required_skills and not parsed.tech_stack:
        return None, "it listed no required skills and no tech stack"
    return parsed, ""


def parse_job_description(llm: LLMProvider, *, jd_text: str) -> ParsedJobDescription:
    """One retry on invalid output, with the rejection reason fed back to the
    model - a malformed or empty answer is usually a one-off, and a pointed
    second attempt is cheaper than surfacing a 502 to the user."""
    user_prompt = jd_text
    reason = ""
    for attempt in range(2):
        try:
            response = llm.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=ParsedJobDescription,
            )
        except (LLMProviderError, LLMTimeoutError) as exc:
            raise JDParseError(f"LLM call failed: {exc}") from exc

        parsed, reason = _validate_output(response.content)
        if parsed is not None:
            return parsed
        user_prompt = (
            f"{jd_text}\n\n---\nYour previous answer was rejected because "
            f"{reason}. Re-read the posting above and fill every field; "
            "extract every skill and technology it mentions."
        )

    raise JDParseError(f"LLM returned invalid output twice: {reason}")


def normalize_jd_text(jd_text: str) -> str:
    # Pasted postings differ in trailing newlines and wrapping depending on
    # where they were copied from - collapse whitespace so those still hit.
    return " ".join(jd_text.split())


def jd_cache_key(*, provider: str, jd_text: str) -> str:
    raw = f"{CACHE_OPERATION}:{PROMPT_VERSION}:{provider}:{normalize_jd_text(jd_text)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def parse_job_description_cached(
    llm: LLMProvider, *, cache: LLMCacheRepository, jd_text: str
) -> ParsedJobDescription:
    """Same contract as parse_job_description, but a posting already parsed
    with this prompt version and provider is served from llm_cache without
    an LLM call. Only validated results are ever written, so a bad answer
    can't get stuck in the cache. The caller commits."""
    key = jd_cache_key(provider=llm.name, jd_text=jd_text)
    cached = cache.get(cache_key=key)
    if cached is not None:
        return ParsedJobDescription.model_validate(cached)

    parsed = parse_job_description(llm, jd_text=jd_text)
    cache.put(
        cache_key=key,
        operation=CACHE_OPERATION,
        result=parsed.model_dump(mode="json"),
    )
    return parsed
