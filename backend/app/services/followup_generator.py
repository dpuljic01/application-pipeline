from pydantic import BaseModel, ValidationError

from app.domain.enums import ApplicationStage
from app.domain.errors import FollowUpGenerationError
from app.integrations.llm.base import LLMProvider, LLMProviderError, LLMTimeoutError


# Lives here, not in api/schemas/: this is the LLM's forced structured-output
# target, not a hand-written API contract - api/schemas/application.py
# imports it for the response shape, not the reverse.
class FollowUpEmail(BaseModel):
    subject: str
    body: str


SYSTEM_PROMPT = """\
You write short, plain follow-up emails for a job applicant to send to a
company they've already applied to or interviewed with.

Hard rules:
- Never use an em dash (—) anywhere in the output. Use a period or comma
  instead. This is a strict requirement, not a style preference.
- Under 120 words for the body. No filler, no generic enthusiasm ("I am
  very passionate about..."), no corporate buzzwords.
- Reference the actual company name and role title naturally, at least
  once. Never write a template with placeholders.
- Plain, professional, direct tone. Write like a competent person sending
  a real email, not like a cover letter.
- Do not invent details (interview dates, names, prior conversations)
  that weren't given to you.

Return a subject line and a body. The subject should be short and specific
to the role, e.g. "Following up: <role title> application" - not generic
like "Following up".
"""


def _stage_context(stage: ApplicationStage) -> str:
    if stage == ApplicationStage.INTERVIEW:
        return (
            "The candidate interviewed for this role and hasn't heard back since. "
            "The email should reference the interview and ask about next steps or "
            "a timeline, without sounding impatient."
        )
    return (
        "The candidate applied for this role and hasn't heard back since. The "
        "email should politely check on the status of the application."
    )


def generate_followup_email(
    llm: LLMProvider,
    *,
    company: str,
    role_title: str,
    stage: ApplicationStage,
    context: str | None,
) -> FollowUpEmail:
    user_prompt = (
        f"Company: {company}\n"
        f"Role: {role_title}\n"
        f"Situation: {_stage_context(stage)}\n"
        f"Additional context from the candidate: {context or 'none'}"
    )

    try:
        response = llm.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=FollowUpEmail,
        )
    except (LLMProviderError, LLMTimeoutError) as exc:
        raise FollowUpGenerationError(f"LLM call failed: {exc}") from exc

    try:
        return FollowUpEmail.model_validate_json(response.content)
    except ValidationError as exc:
        raise FollowUpGenerationError(
            f"LLM returned invalid structured output: {exc}"
        ) from exc
