"""Pre-fills the Profile page from a CV. Suggestion only: nothing here is
saved - the user reviews the filled-in form and saves it through the normal
PUT /profile. The CV itself is never stored either; its text lives only for
the duration of this request."""

from io import BytesIO
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.db.mixins import utcnow
from app.domain.errors import CVExtractionError, InvalidCV
from app.integrations.llm.base import LLMProvider, LLMProviderError, LLMTimeoutError
from app.services.jd_parser import SKILL_NAMING_RULES, Seniority

# Cap on what's sent to the LLM - a 2-3 page CV is ~4-8k characters, so this
# only ever cuts off something that isn't really a CV.
MAX_CV_CHARS = 30_000

# Same labels the Profile page's level dropdown offers, so an extracted
# level lands on a real option instead of the "Other" free-text fallback.
LanguageLevel = Literal[
    "Native",
    "Fluent (C2)",
    "Advanced (C1)",
    "Upper-Intermediate (B2)",
    "Intermediate (B1)",
    "Elementary (A2)",
    "Beginner (A1)",
]


class CVLanguage(BaseModel):
    language: str
    level: LanguageLevel


class CVExtraction(BaseModel):
    """LLM structured-output target, and the endpoint's response shape -
    every field required-but-nullable, same reasoning as ParsedJobDescription."""

    skills: list[str] = Field(
        description="Technical skills, tools, frameworks, and platforms"
    )
    years_experience: int | None = Field(
        description=(
            "Total years of professional experience in the candidate's field, "
            "from the work history dates; null if it can't be determined"
        )
    )
    languages: list[CVLanguage] = Field(
        description="Spoken/written languages only, not programming languages"
    )
    seniority: Seniority | None = Field(
        description="Seniority level the candidate's experience supports today"
    )


SYSTEM_PROMPT = (
    """\
You extract a candidate's profile from their CV for a job-matching tool.

Only extract what the CV actually supports. Never invent skills or inflate
experience. Include skills from both a skills section and the work history
(technologies used in described projects count). Leave out soft skills
("teamwork", "communication").

Years of experience: count professional roles only (not education), merge
overlapping periods, and round down. Null if dates are missing.

Language levels: map the CV's wording onto the allowed levels - "mother
tongue" is Native, "business fluent"/"verhandlungssicher" is Fluent (C2),
CEFR levels map directly. If no level is given, choose the most plausible
one from context.

"""
    + SKILL_NAMING_RULES
)


def extract_text_from_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except (PdfReadError, ValueError) as exc:
        raise InvalidCV("Could not read the PDF") from exc
    if not text.strip():
        # Scanned/image-only PDFs have no text layer.
        raise InvalidCV(
            "No text found in the PDF - it may be a scanned image. "
            "Paste the CV text instead."
        )
    return text


def extract_profile_from_cv(llm: LLMProvider, *, cv_text: str) -> CVExtraction:
    cv_text = cv_text.strip()
    if not cv_text:
        raise InvalidCV("The CV is empty")

    try:
        response = llm.complete(
            system_prompt=SYSTEM_PROMPT,
            # Without today's date the model can't resolve "2021 - present"
            # and undercounts (verified live: 8 years came back as 5).
            user_prompt=f"Today's date: {utcnow().date().isoformat()}\n\n"
            f"{cv_text[:MAX_CV_CHARS]}",
            response_schema=CVExtraction,
            max_tokens=2048,
        )
    except (LLMProviderError, LLMTimeoutError) as exc:
        raise CVExtractionError(f"LLM call failed: {exc}") from exc

    try:
        return CVExtraction.model_validate_json(response.content)
    except ValidationError as exc:
        raise CVExtractionError(
            f"LLM returned invalid structured output: {exc}"
        ) from exc
