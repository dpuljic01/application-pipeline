from __future__ import annotations

import re

from pydantic import ValidationError

from app.api.schemas.jd_parse import ParsedJobDescription
from app.api.schemas.match import MatchInsights
from app.api.schemas.profile import ProfileRead
from app.db.mixins import utcnow
from app.db.models.profile import Profile
from app.domain.errors import MatchingError
from app.integrations.llm.base import LLMProvider, LLMProviderError, LLMTimeoutError

SENIORITY_ORDER = ["junior", "mid", "senior", "staff"]


def _score_skills(profile: ProfileRead, parsed_jd: ParsedJobDescription) -> dict:
    profile_set = {s.strip().lower() for s in profile.skills}
    required_pool = {s.strip().lower() for s in parsed_jd.required_skills} | {
        s.strip().lower() for s in parsed_jd.tech_stack
    }
    nice_pool = {s.strip().lower() for s in parsed_jd.nice_to_have_skills}

    required_score = (
        30
        if not required_pool
        else round(30 * len(profile_set & required_pool) / len(required_pool))
    )
    nice_score = (
        10
        if not nice_pool
        else round(10 * len(profile_set & nice_pool) / len(nice_pool))
    )

    return {
        "score": required_score + nice_score,
        "max": 40,
        "matched_required": sorted(profile_set & required_pool),
        "matched_nice_to_have": sorted(profile_set & nice_pool),
    }


def _score_seniority(profile: ProfileRead, parsed_jd: ParsedJobDescription) -> dict:
    targets = [t for t in profile.target_seniorities if t in SENIORITY_ORDER]
    assessed = parsed_jd.seniority_assessed

    if not targets:
        # Profile not filled in yet - don't penalize.
        score = 10
    elif assessed in targets:
        score = 20
    elif assessed not in SENIORITY_ORDER:
        score = 10
    else:
        assessed_idx = SENIORITY_ORDER.index(assessed)
        distance = min(abs(assessed_idx - SENIORITY_ORDER.index(t)) for t in targets)
        score = 10 if distance == 1 else 0

    return {"score": score, "max": 20, "assessed": assessed, "targets": targets}


def _score_languages(profile: ProfileRead, parsed_jd: ParsedJobDescription) -> dict:
    required = parsed_jd.languages
    if not required:
        return {"score": 15, "max": 15, "matched": [], "missing": []}

    profile_langs = {entry.language.strip().lower() for entry in profile.languages}
    matched = [lang for lang in required if lang.strip().lower() in profile_langs]
    missing = [lang for lang in required if lang.strip().lower() not in profile_langs]

    return {
        "score": round(15 * len(matched) / len(required)),
        "max": 15,
        "matched": matched,
        "missing": missing,
    }


def parse_salary_midpoint_chf(text: str | None) -> int | None:
    """Best-effort extraction of a numeric salary (or range midpoint) from
    free text like "CHF 95'000 - 125'000" or "95k-125k". Returns None for
    anything unparseable - callers must treat that as neutral, never as a
    penalty (this text is LLM-generated, not something to invent data for)."""
    if not text:
        return None

    numbers = re.findall(r"\d[\d'.,]*", text)
    is_k_shorthand = bool(re.search(r"\d\s*k\b", text, re.IGNORECASE))
    values = []
    for raw in numbers:
        cleaned = raw.strip("'.,").replace("'", "").replace(",", "").replace(".", "")
        if not cleaned:
            continue
        value = int(cleaned)
        if is_k_shorthand and value < 1000:
            value *= 1000
        values.append(value)

    if not values:
        return None

    first_two = values[:2]
    return round(sum(first_two) / len(first_two))


def _score_salary(profile: ProfileRead, parsed_jd: ParsedJobDescription) -> dict:
    midpoint = parse_salary_midpoint_chf(parsed_jd.salary_range)
    floor = profile.min_salary_chf
    ideal = profile.ideal_salary_chf

    if midpoint is None or floor is None or ideal is None or ideal <= floor:
        return {"score": 8, "max": 15, "posting_midpoint_chf": midpoint}

    if midpoint >= ideal:
        score = 15
    elif midpoint <= floor:
        score = 0
    else:
        score = round(15 * (midpoint - floor) / (ideal - floor))

    return {"score": score, "max": 15, "posting_midpoint_chf": midpoint}


def _score_remote_policy(parsed_jd: ParsedJobDescription) -> dict:
    policy = (parsed_jd.remote_policy or "").strip().lower()

    if not policy or "remote" in policy or "hybrid" in policy:
        score = 10
    elif "onsite" in policy or "on-site" in policy or "on site" in policy:
        score = 6
    else:
        score = 8  # unrecognized text, lenient

    return {"score": score, "max": 10, "policy": parsed_jd.remote_policy}


def compute_rule_based_components(
    *, profile: ProfileRead, parsed_jd: ParsedJobDescription
) -> dict[str, dict]:
    return {
        "skills": _score_skills(profile, parsed_jd),
        "seniority": _score_seniority(profile, parsed_jd),
        "language": _score_languages(profile, parsed_jd),
        "salary": _score_salary(profile, parsed_jd),
        "remote_policy": _score_remote_policy(parsed_jd),
    }


MATCH_SYSTEM_PROMPT = """\
You are an honest, conservative career-fit assessor. Compare a candidate's
profile against a specific job posting and produce a short, candid read of
the fit - never oversell, never invent skills or experience the candidate
doesn't have.

If the candidate's home location and the posting's location/remote policy
suggest a difficult onsite commute (e.g. different countries or distant
regions, and the role is not remote/hybrid), mention it as a gap - use your
own knowledge of geography, don't guess distances you're unsure of. If the
candidate's home location is not provided, don't speculate about commute at
all.

Be specific and grounded in the actual posting text, not generic advice.
"""


def _build_match_user_prompt(
    *,
    profile: ProfileRead,
    parsed_jd: ParsedJobDescription,
    application_location: str | None,
) -> str:
    profile_summary = (
        f"Years of experience: {profile.years_experience if profile.years_experience is not None else 'not stated'}\n"
        f"Skills: {', '.join(profile.skills) or 'not stated'}\n"
        f"Languages: {', '.join(f'{entry.language} ({entry.level})' for entry in profile.languages) or 'not stated'}\n"
        f"Target seniority: {', '.join(profile.target_seniorities) or 'not stated'}\n"
        f"Home location: {profile.home_location or 'not stated'}"
    )
    return (
        f"CANDIDATE PROFILE\n{profile_summary}\n\n"
        f"JOB POSTING LOCATION: {application_location or 'not stated'}\n\n"
        f"PARSED JOB DESCRIPTION (JSON)\n{parsed_jd.model_dump_json()}"
    )


def generate_match_insights(
    llm: LLMProvider,
    *,
    profile: ProfileRead,
    parsed_jd: ParsedJobDescription,
    application_location: str | None,
) -> MatchInsights:
    user_prompt = _build_match_user_prompt(
        profile=profile, parsed_jd=parsed_jd, application_location=application_location
    )
    try:
        response = llm.complete(
            system_prompt=MATCH_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=MatchInsights,
        )
    except (LLMProviderError, LLMTimeoutError) as exc:
        raise MatchingError(f"LLM call failed: {exc}") from exc

    try:
        return MatchInsights.model_validate_json(response.content)
    except ValidationError as exc:
        raise MatchingError(f"LLM returned invalid structured output: {exc}") from exc


def score_application_match(
    llm: LLMProvider,
    *,
    profile: Profile,
    parsed_jd: ParsedJobDescription,
    application_location: str | None,
) -> dict:
    profile_read = ProfileRead.model_validate(profile)

    components = compute_rule_based_components(
        profile=profile_read, parsed_jd=parsed_jd
    )
    rule_score = sum(c["score"] for c in components.values())

    insights = generate_match_insights(
        llm,
        profile=profile_read,
        parsed_jd=parsed_jd,
        application_location=application_location,
    )

    return {
        "rule_score": rule_score,
        "components": components,
        "insights": insights.model_dump(),
        "scored_at": utcnow().isoformat(),
    }
