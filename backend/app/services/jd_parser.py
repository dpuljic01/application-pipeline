from pydantic import ValidationError

from app.api.schemas.jd_parse import ParsedJobDescription
from app.domain.errors import JDParseError
from app.integrations.llm.base import LLMProvider, LLMProviderError, LLMTimeoutError

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


def parse_job_description(llm: LLMProvider, jd_text: str) -> ParsedJobDescription:
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
