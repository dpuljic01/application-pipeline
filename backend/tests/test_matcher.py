import pytest

from app.db.models.profile import Profile
from app.services.jd_parser import ParsedJobDescription
from app.services.matcher import (
    compute_rule_based_components,
    compute_rule_score,
    parse_salary_midpoint_chf,
    profile_language_level,
)


def make_profile(**overrides) -> Profile:
    # matcher.py operates on the ORM Profile object directly, not a Pydantic
    # Read schema - languages is a JSONB column, so entries are plain dicts.
    defaults = dict(
        years_experience=7,
        skills=["Python", "FastAPI", "Docker"],
        languages=[{"language": "English", "level": "fluent"}],
        target_seniorities=["mid", "senior"],
        min_salary_chf=90_000,
        ideal_salary_chf=120_000,
        home_location="Thalwil, Switzerland",
    )
    defaults.update(overrides)
    return Profile(**defaults)


def make_jd(**overrides) -> ParsedJobDescription:
    defaults = dict(
        required_skills=["Python", "FastAPI"],
        nice_to_have_skills=["Docker"],
        seniority_claimed="Senior",
        seniority_assessed="senior",
        tech_stack=["Python", "FastAPI"],
        languages=["English"],
        years_experience_min=5,
        remote_policy="hybrid",
        salary_range="CHF 95'000 - 125'000",
        salary_confidence="stated",
        key_responsibilities=["Build things"],
        red_flags=[],
        missing_info=[],
        summary="A role.",
    )
    defaults.update(overrides)
    return ParsedJobDescription(**defaults)


# --- salary ---------------------------------------------------------------


def test_score_salary_at_floor_returns_zero():
    profile = make_profile(min_salary_chf=90_000, ideal_salary_chf=120_000)
    jd = make_jd(salary_range="CHF 90'000")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["salary"]["score"] == 0


def test_score_salary_below_floor_returns_zero():
    profile = make_profile(min_salary_chf=90_000, ideal_salary_chf=120_000)
    jd = make_jd(salary_range="CHF 70'000")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["salary"]["score"] == 0


def test_score_salary_at_ideal_returns_full():
    profile = make_profile(min_salary_chf=90_000, ideal_salary_chf=120_000)
    jd = make_jd(salary_range="CHF 120'000")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["salary"]["score"] == 15


def test_score_salary_above_ideal_caps_at_full():
    profile = make_profile(min_salary_chf=90_000, ideal_salary_chf=120_000)
    jd = make_jd(salary_range="CHF 150'000")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["salary"]["score"] == 15


def test_score_salary_midpoint_interpolates_between_floor_and_ideal():
    profile = make_profile(min_salary_chf=90_000, ideal_salary_chf=120_000)
    jd = make_jd(salary_range="CHF 105'000")  # exact midpoint of floor/ideal
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["salary"]["score"] == round(15 * 0.5)


def test_score_salary_unparseable_posting_text_returns_neutral():
    profile = make_profile(min_salary_chf=90_000, ideal_salary_chf=120_000)
    jd = make_jd(salary_range="Competitive")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["salary"]["score"] == 8


def test_score_salary_unset_profile_fields_returns_neutral():
    profile = make_profile(min_salary_chf=None, ideal_salary_chf=None)
    jd = make_jd(salary_range="CHF 95'000 - 125'000")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["salary"]["score"] == 8


@pytest.mark.parametrize(
    "text,expected",
    [
        ("CHF 95'000 - 125'000", 110_000),
        ("95k-125k", 110_000),
        ("120000", 120_000),
        ("competitive", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_salary_midpoint_chf(text, expected):
    assert parse_salary_midpoint_chf(text) == expected


# --- seniority --------------------------------------------------------------


@pytest.mark.parametrize("assessed", ["mid", "senior"])
def test_score_seniority_both_targeted_scores_full(assessed):
    profile = make_profile(target_seniorities=["mid", "senior"])
    jd = make_jd(seniority_assessed=assessed)
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["seniority"]["score"] == 20


def test_score_seniority_one_step_off_gets_partial_credit():
    profile = make_profile(target_seniorities=["mid", "senior"])
    jd = make_jd(seniority_assessed="junior")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["seniority"]["score"] == 10


def test_score_seniority_two_steps_off_scores_zero():
    profile = make_profile(target_seniorities=["junior"])
    jd = make_jd(seniority_assessed="staff")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["seniority"]["score"] == 0


def test_score_seniority_empty_target_list_is_neutral():
    profile = make_profile(target_seniorities=[])
    jd = make_jd(seniority_assessed="staff")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["seniority"]["score"] == 10


# --- skills -------------------------------------------------------------


def test_score_skills_full_overlap():
    profile = make_profile(skills=["Python", "FastAPI", "Docker"])
    jd = make_jd(
        required_skills=["Python", "FastAPI"],
        tech_stack=[],
        nice_to_have_skills=["Docker"],
    )
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["skills"]["score"] == 40


def test_score_skills_partial_overlap():
    profile = make_profile(skills=["Python"])
    jd = make_jd(
        required_skills=["Python", "Kubernetes"],
        tech_stack=[],
        nice_to_have_skills=[],
    )
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    # half of the 30-point required slice (15) + full 10 for the empty,
    # not-penalized nice-to-have list
    assert components["skills"]["score"] == 25


def test_score_skills_empty_required_list_does_not_penalize():
    profile = make_profile(skills=[])
    jd = make_jd(required_skills=[], tech_stack=[], nice_to_have_skills=[])
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["skills"]["score"] == 40


def test_score_skills_empty_profile_skills_scores_zero_for_stated_requirements():
    profile = make_profile(skills=[])
    jd = make_jd(required_skills=["Python"], tech_stack=[], nice_to_have_skills=[])
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    # 0/30 required (no overlap) + full 10 for the empty, not-penalized
    # nice-to-have list
    assert components["skills"]["score"] == 10


# --- languages -------------------------------------------------------------


def test_score_languages_all_present():
    profile = make_profile(
        languages=[
            {"language": "English", "level": "fluent"},
            {"language": "German", "level": "B1"},
        ]
    )
    jd = make_jd(languages=["English", "German"])
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["language"]["score"] == 15


def test_score_languages_missing_one():
    profile = make_profile(languages=[{"language": "English", "level": "fluent"}])
    jd = make_jd(languages=["English", "French"])
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["language"]["score"] == round(15 * 0.5)


def test_score_languages_empty_requirement_scores_full():
    profile = make_profile(languages=[])
    jd = make_jd(languages=[])
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["language"]["score"] == 15


# --- remote policy -----------------------------------------------------------


@pytest.mark.parametrize("policy", ["remote", "hybrid", None, ""])
def test_score_remote_policy_remote_or_hybrid_full_marks(policy):
    profile = make_profile()
    jd = make_jd(remote_policy=policy)
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["remote_policy"]["score"] == 10


def test_score_remote_policy_onsite_gets_flat_neutral_score():
    profile = make_profile()
    jd = make_jd(remote_policy="onsite")
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    assert components["remote_policy"]["score"] == 6


# --- total -------------------------------------------------------------


def test_compute_rule_based_components_total_never_exceeds_100():
    profile = make_profile()
    jd = make_jd()
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    total = sum(c["score"] for c in components.values())
    assert 0 <= total <= 100


# --- language levels ------------------------------------------------------


def _lang_req(language, min_level, required=True):
    return {"language": language, "min_level": min_level, "required": required}


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Native", "native"),
        ("Fluent (C2)", "C2"),
        ("Advanced (C1)", "C1"),
        ("Upper-Intermediate (B2)", "B2"),
        ("Intermediate (B1)", "B1"),
        ("upper intermediate", "B2"),
        ("verhandlungssicher", "C2"),
        ("b1", "B1"),
        ("conversational-ish", None),
    ],
)
def test_profile_language_level(label, expected):
    assert profile_language_level(label) == expected


@pytest.mark.parametrize(
    ("required", "have", "score"),
    [
        ("C2", "Native", 15),  # exceeds
        ("C2", "Fluent (C2)", 15),  # meets
        ("C2", "Advanced (C1)", 8),  # one level short -> half credit (7.5)
        ("C2", "Intermediate (B1)", 0),  # fluent German vs B1: the demo bug
        (None, "Beginner (A1)", 15),  # posting states no level
        ("C1", "some german", 15),  # unreadable profile level is neutral
    ],
)
def test_language_score_compares_levels(required, have, score):
    profile = make_profile(languages=[{"language": "German", "level": have}])
    jd = make_jd(languages=[_lang_req("German", required)])
    assert (
        compute_rule_based_components(profile=profile, parsed_jd=jd)["language"][
            "score"
        ]
        == score
    )


def test_preferred_languages_cost_nothing():
    profile = make_profile(languages=[{"language": "English", "level": "Native"}])
    jd = make_jd(
        languages=[
            _lang_req("English", "C1"),
            _lang_req("German", "B2", required=False),
        ]
    )
    assert (
        compute_rule_based_components(profile=profile, parsed_jd=jd)["language"][
            "score"
        ]
        == 15
    )


def test_missing_required_language_scores_zero_for_it():
    profile = make_profile(languages=[{"language": "English", "level": "Native"}])
    jd = make_jd(languages=[_lang_req("English", "C1"), _lang_req("French", "B2")])
    component = compute_rule_based_components(profile=profile, parsed_jd=jd)["language"]
    assert component["score"] == 8  # 15 * 0.5, rounded
    assert component["requirements"][1]["your_level"] == "missing"


# --- skill gate + core-skill cap -------------------------------------------


def _total(profile, jd):
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    return compute_rule_score(profile=profile, components=components)


def test_good_stack_match_is_not_gated():
    total, adjustments = _total(make_profile(), make_jd(core_skills=["Python"]))
    assert adjustments == []
    assert total > 80


def test_weak_stack_match_scales_down_everything_else():
    # 1 of 5 required skills (20%): non-skill points count 20/60 = a third.
    profile = make_profile(skills=["Docker"])
    jd = make_jd(
        required_skills=["Java", "Spring Boot", "Kafka", "Oracle", "Docker"],
        tech_stack=[],
        nice_to_have_skills=[],
    )
    components = compute_rule_based_components(profile=profile, parsed_jd=jd)
    others = sum(c["score"] for n, c in components.items() if n != "skills")

    total, adjustments = compute_rule_score(profile=profile, components=components)

    assert total == components["skills"]["score"] + round(others / 3)
    assert "20% of required skills" in adjustments[0]


def test_missing_core_skill_caps_total_even_with_a_decent_ratio():
    # Knows 4 of 5 required (80%, no gate) but not Go, the language of the job.
    profile = make_profile(skills=["Docker", "Kubernetes", "PostgreSQL", "AWS"])
    jd = make_jd(
        required_skills=["Go", "Docker", "Kubernetes", "PostgreSQL", "AWS"],
        tech_stack=[],
        core_skills=["Go"],
    )

    total, adjustments = _total(profile, jd)

    assert total == 35
    assert any("Missing core skill (Go)" in a for a in adjustments)


def test_core_skill_match_is_case_insensitive():
    profile = make_profile(skills=["python", "FastAPI"])
    total, adjustments = _total(profile, make_jd(core_skills=["Python"]))
    assert adjustments == []


def test_empty_profile_skills_are_not_gated_or_capped():
    profile = make_profile(skills=[])
    total, adjustments = _total(profile, make_jd(core_skills=["Python"]))
    components = compute_rule_based_components(profile=profile, parsed_jd=make_jd())
    assert total == sum(c["score"] for c in components.values())
    assert adjustments == ["Add skills to your profile for an accurate score."]


def test_aws_umbrella_matches_specific_services_both_ways():
    jd = make_jd(required_skills=["AWS ECS", "AWS RDS"], tech_stack=[], core_skills=[])
    skills = compute_rule_based_components(
        profile=make_profile(skills=["AWS"]), parsed_jd=jd
    )["skills"]
    assert skills["required_ratio"] == 1.0

    jd = make_jd(required_skills=["AWS"], tech_stack=[], core_skills=[])
    skills = compute_rule_based_components(
        profile=make_profile(skills=["AWS Lambda"]), parsed_jd=jd
    )["skills"]
    assert skills["required_ratio"] == 1.0


def test_umbrella_does_not_match_unrelated_prefixes():
    jd = make_jd(required_skills=["AWSome Framework"], tech_stack=[], core_skills=[])
    skills = compute_rule_based_components(
        profile=make_profile(skills=["AWS"]), parsed_jd=jd
    )["skills"]
    assert skills["required_ratio"] == 0.0


def test_nice_to_haves_listed_in_tech_stack_are_not_required():
    jd = make_jd(
        required_skills=["Python"],
        tech_stack=["Python", "Spark"],
        nice_to_have_skills=["Spark"],
    )
    skills = compute_rule_based_components(
        profile=make_profile(skills=["Python"]), parsed_jd=jd
    )["skills"]
    assert skills["required_ratio"] == 1.0


def test_partially_matched_core_scales_the_cap():
    # Has Terraform, not Kubernetes: cap = 35 + 65 * 0.5 = 68 (rounded).
    profile = make_profile(skills=["Terraform", "AWS", "Python", "Docker"])
    jd = make_jd(
        required_skills=["Kubernetes", "Terraform", "AWS", "Python", "Docker"],
        tech_stack=[],
        core_skills=["Kubernetes", "Terraform"],
    )

    total, adjustments = _total(profile, jd)

    assert total == 68
    assert "Missing core skill (Kubernetes): capped at 68" in adjustments[0]
