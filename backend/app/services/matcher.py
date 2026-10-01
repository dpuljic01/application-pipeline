from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.db.mixins import utcnow
from app.db.models.profile import Profile
from app.domain.errors import MatchingError
from app.integrations.llm.base import LLMProvider, LLMProviderError, LLMTimeoutError
from app.services.jd_parser import LANGUAGE_LEVEL_ORDER, ParsedJobDescription

SENIORITY_ORDER = ["junior", "mid", "senior", "staff"]

# Below this share of required skills matched, the non-skill components are
# scaled down proportionally (at 30% matched they count half). Tapered, not
# a cliff: a hard "<25% -> cap" makes 24% and 26% score wildly differently.
SKILL_GATE_RATIO = 0.6
# Ceiling when none of the posting's core skills (usually the main
# programming language) is on the profile - the rest of the fit can't
# compensate for not knowing the language the job is written in. With some
# core skills matched the ceiling rises linearly to 100 (no cap) at all of
# them: missing half the core is serious, but parsers sometimes list
# accepted alternatives ("Python or Go") as two core skills, so "any core
# skill missing -> 35" would punish a correct match.
CORE_SKILL_MISSING_CAP = 35


# --- output shapes -----------------------------------------------------
# Live here, not in api/schemas/: MatchInsights is the LLM's forced
# structured-output target (a business-logic concern), and MatchDetails is
# what this module actually produces. api/schemas/application.py imports
# these for its response shape, not the other way around - matcher.py has
# no reason to know or care that its result ends up in an HTTP response.


class MatchInsights(BaseModel):
    """LLM-generated qualitative read of fit, alongside the deterministic
    rule-based score. Never changes the numeric match_score itself."""

    fit_narrative: str = Field(
        description="2-4 sentence honest assessment of fit, including gaps"
    )
    key_strengths: list[str]
    gaps: list[str]
    talking_points: list[str] = Field(
        description="Cover-letter-ready points connecting the candidate's profile to this specific role"
    )


class MatchComponentScore(BaseModel):
    model_config = ConfigDict(extra="allow")

    score: int
    max: int


class MatchDetails(BaseModel):
    rule_score: int
    components: dict[str, MatchComponentScore]
    # Human-readable reasons rule_score is lower than the component sum.
    # Defaulted so match_details stored before this existed still load.
    adjustments: list[str] = []
    insights: MatchInsights
    scored_at: str


# --- rule-based scoring --------------------------------------------------
# Operates on the ORM Profile object directly (not a Pydantic Read schema):
# matcher.py is a service, and services work with ORM objects, the same way
# ApplicationService never converts Application into a Pydantic type
# internally. `languages` is a JSONB column, so its entries are plain
# dicts here, not LanguageEntry objects.


# Cloud providers whose services are named "<provider> <service>" (see
# SKILL_NAMING_RULES). "AWS" on a profile counts for "AWS ECS" in a posting
# and vice versa - someone listing AWS has used *some* of its services, and
# a posting asking for "AWS" is satisfied by experience with any of them.
CLOUD_UMBRELLAS = ("aws", "azure", "gcp")


def _norm(skill: str) -> str:
    return skill.strip().lower()


def _has_skill(profile_set: set[str], skill: str) -> bool:
    skill = _norm(skill)
    if skill in profile_set:
        return True
    for umbrella in CLOUD_UMBRELLAS:
        if skill == umbrella and any(p.startswith(umbrella + " ") for p in profile_set):
            return True
        if skill.startswith(umbrella + " ") and umbrella in profile_set:
            return True
    return False


def _score_skills(*, profile: Profile, parsed_jd: ParsedJobDescription) -> dict:
    profile_set = {_norm(s) for s in profile.skills}
    nice_pool = {_norm(s) for s in parsed_jd.nice_to_have_skills}
    # tech_stack minus nice-to-haves: the parser is told to keep them apart,
    # but a stray nice-to-have there must not count as a hard requirement.
    required_pool = (
        {_norm(s) for s in parsed_jd.required_skills}
        | {_norm(s) for s in parsed_jd.tech_stack}
    ) - nice_pool
    matched_required = {s for s in required_pool if _has_skill(profile_set, s)}
    matched_nice = {s for s in nice_pool if _has_skill(profile_set, s)}

    required_ratio = (
        1.0 if not required_pool else len(matched_required) / len(required_pool)
    )
    required_score = round(30 * required_ratio)
    nice_score = 10 if not nice_pool else round(10 * len(matched_nice) / len(nice_pool))

    return {
        "score": required_score + nice_score,
        "max": 40,
        "matched_required": sorted(matched_required),
        "matched_nice_to_have": sorted(matched_nice),
        "required_ratio": round(required_ratio, 2),
        "core_skills": parsed_jd.core_skills,
        "matched_core": [
            s for s in parsed_jd.core_skills if _has_skill(profile_set, s)
        ],
    }


def _score_seniority(*, profile: Profile, parsed_jd: ParsedJobDescription) -> dict:
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


# Profile levels are the Profile page's labels ("Advanced (C1)", "Native"),
# or free text for "Other" - read a CEFR code if present, else keywords.
_LEVEL_KEYWORDS = [
    ("native", "native"),
    ("mother", "native"),
    ("muttersprache", "native"),
    ("fluent", "C2"),
    ("verhandlungssicher", "C2"),
    ("fliessend", "C2"),
    ("upper", "B2"),
    ("advanced", "C1"),
    ("intermediate", "B1"),
    ("elementary", "A2"),
    ("basic", "A2"),
    ("beginner", "A1"),
]


def profile_language_level(level: str) -> str | None:
    text = level.strip().lower()
    cefr = re.search(r"\b([abc][12])\b", text)
    if cefr:
        return cefr.group(1).upper()
    for keyword, mapped in _LEVEL_KEYWORDS:
        if keyword in text:
            return mapped
    return None


def _language_credit(*, required: str | None, have: str | None) -> float:
    """1.0 meets the level, 0.5 one step short, 0 otherwise. Unknown levels
    on either side count as met - missing data is neutral, not a penalty."""
    if required is None or have is None:
        return 1.0
    shortfall = LANGUAGE_LEVEL_ORDER.index(required) - LANGUAGE_LEVEL_ORDER.index(have)
    if shortfall <= 0:
        return 1.0
    return 0.5 if shortfall == 1 else 0.0


def _score_languages(*, profile: Profile, parsed_jd: ParsedJobDescription) -> dict:
    # Only hard requirements count; "German is a plus" can't cost points.
    required = [req for req in parsed_jd.languages if req.required]
    if not required:
        return {"score": 15, "max": 15, "requirements": []}

    profile_levels = {
        entry["language"].strip().lower(): profile_language_level(entry["level"])
        for entry in profile.languages
    }
    results = []
    for req in required:
        key = req.language.strip().lower()
        if key not in profile_levels:
            credit, have = 0.0, None
        else:
            have = profile_levels[key]
            credit = _language_credit(required=req.min_level, have=have)
        results.append(
            {
                "language": req.language,
                "required_level": req.min_level,
                "your_level": have if key in profile_levels else "missing",
                "credit": credit,
            }
        )

    return {
        "score": round(15 * sum(r["credit"] for r in results) / len(results)),
        "max": 15,
        "requirements": results,
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


def _score_salary(*, profile: Profile, parsed_jd: ParsedJobDescription) -> dict:
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


def _score_remote_policy(*, parsed_jd: ParsedJobDescription) -> dict:
    policy = (parsed_jd.remote_policy or "").strip().lower()

    if not policy or "remote" in policy or "hybrid" in policy:
        score = 10
    elif "onsite" in policy or "on-site" in policy or "on site" in policy:
        score = 6
    else:
        score = 8  # unrecognized text, lenient

    return {"score": score, "max": 10, "policy": parsed_jd.remote_policy}


def compute_rule_score(
    *, profile: Profile, components: dict[str, dict]
) -> tuple[int, list[str]]:
    """Combines the components into the final 0-100 score. Not a plain sum:
    the stack has to fit before salary, seniority or remote policy matter."""
    skills = components["skills"]
    others = sum(c["score"] for name, c in components.items() if name != "skills")

    if not profile.skills:
        # Can't judge the stack against an empty profile - don't gate on it.
        return skills["score"] + others, [
            "Add skills to your profile for an accurate score."
        ]

    adjustments = []
    ratio = skills["required_ratio"]
    if ratio < SKILL_GATE_RATIO:
        factor = ratio / SKILL_GATE_RATIO
        scaled = round(others * factor)
        adjustments.append(
            f"Only {round(ratio * 100)}% of required skills matched, so "
            f"seniority, language, salary and remote count {round(factor * 100)}% "
            f"({others} -> {scaled} points)."
        )
        others = scaled

    total = skills["score"] + others
    core = skills["core_skills"]
    if core:
        core_ratio = len(skills["matched_core"]) / len(core)
        cap = round(
            CORE_SKILL_MISSING_CAP + (100 - CORE_SKILL_MISSING_CAP) * core_ratio
        )
        if total > cap:
            missing = [s for s in core if s not in skills["matched_core"]]
            adjustments.append(
                f"Missing core skill ({', '.join(missing)}): capped at {cap} "
                f"(was {total})."
            )
            total = cap

    return total, adjustments


def compute_rule_based_components(
    *, profile: Profile, parsed_jd: ParsedJobDescription
) -> dict[str, dict]:
    return {
        "skills": _score_skills(profile=profile, parsed_jd=parsed_jd),
        "seniority": _score_seniority(profile=profile, parsed_jd=parsed_jd),
        "language": _score_languages(profile=profile, parsed_jd=parsed_jd),
        "salary": _score_salary(profile=profile, parsed_jd=parsed_jd),
        "remote_policy": _score_remote_policy(parsed_jd=parsed_jd),
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
    profile: Profile,
    parsed_jd: ParsedJobDescription,
    application_location: str | None,
) -> str:
    languages = ", ".join(
        f"{entry['language']} ({entry['level']})" for entry in profile.languages
    )
    profile_summary = (
        f"Years of experience: {profile.years_experience if profile.years_experience is not None else 'not stated'}\n"
        f"Skills: {', '.join(profile.skills) or 'not stated'}\n"
        f"Languages: {languages or 'not stated'}\n"
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
    profile: Profile,
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
) -> MatchDetails:
    components = compute_rule_based_components(profile=profile, parsed_jd=parsed_jd)
    rule_score, adjustments = compute_rule_score(profile=profile, components=components)

    insights = generate_match_insights(
        llm,
        profile=profile,
        parsed_jd=parsed_jd,
        application_location=application_location,
    )

    return MatchDetails(
        rule_score=rule_score,
        components=components,
        adjustments=adjustments,
        insights=insights,
        scored_at=utcnow().isoformat(),
    )
