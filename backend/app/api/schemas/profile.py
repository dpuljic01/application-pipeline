from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.jd_parse import Seniority


class LanguageEntry(BaseModel):
    language: str = Field(min_length=1, max_length=60)
    level: str = Field(min_length=1, max_length=60)


class ProfileUpdate(BaseModel):
    years_experience: int | None = Field(default=None, ge=0, le=60)
    skills: list[str] | None = None
    languages: list[LanguageEntry] | None = None
    # Subset of junior/mid/senior/staff the user will accept - reuses the
    # same Literal jd_parse.py uses for the LLM's seniority_assessed output,
    # so matcher.py can compare them directly with no conversion.
    target_seniorities: list[Seniority] | None = None
    min_salary_chf: int | None = Field(default=None, ge=0)
    ideal_salary_chf: int | None = Field(default=None, ge=0)
    home_location: str | None = Field(default=None, max_length=120)


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    years_experience: int | None
    skills: list[str]
    languages: list[LanguageEntry]
    target_seniorities: list[Seniority]
    min_salary_chf: int | None
    ideal_salary_chf: int | None
    home_location: str | None
