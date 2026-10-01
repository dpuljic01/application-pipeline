"""Generates app/services/demo_seed.json - the demo account's data.

Runs each fictional posting below through the real JD parser and matcher
(and one follow-up draft) once, so the demo shows genuine model output, then
freezes the result as JSON. Seeding the demo account itself (on every demo
login) only reads that file: no LLM calls, no cost, deterministic.

Re-run after changing prompts or the output schemas:
    cd backend && PYTHONPATH=. uv run python scripts/generate_demo_seed.py

Every company and person here is fictional.
"""

import json
from pathlib import Path

from app.db.models.profile import Profile
from app.domain.enums import ApplicationStage
from app.integrations.llm.factory import get_llm_provider
from app.services.followup_generator import generate_followup_email
from app.services.jd_parser import parse_job_description
from app.services.matcher import score_application_match

OUT = Path(__file__).resolve().parents[1] / "app" / "services" / "demo_seed.json"

PROFILE = {
    "years_experience": 6,
    "skills": [
        "Python",
        "FastAPI",
        "Django",
        "PostgreSQL",
        "SQLAlchemy",
        "Docker",
        "AWS",
        "Terraform",
        "GitHub Actions",
        "Redis",
        "REST APIs",
        "pytest",
        "Linux",
        "TypeScript",
    ],
    "languages": [
        {"language": "English", "level": "Fluent (C2)"},
        {"language": "German", "level": "Intermediate (B1)"},
        {"language": "Italian", "level": "Native"},
    ],
    "target_seniorities": ["mid", "senior"],
    "min_salary_chf": 105000,
    "ideal_salary_chf": 130000,
    "home_location": "Zurich, Switzerland",
}

# history: (stage, days_ago) after the initial SAVED; activities: extra
# timeline entries (type, days_ago, note). days_ago counts back from seed time.
APPLICATIONS = [
    {
        "company": "Northgate AG",
        "role_title": "Senior Backend Engineer (Python)",
        "location": "Zurich",
        "salary_range": "CHF 120'000 - 140'000",
        "created_days_ago": 21,
        "history": [("APPLIED", 18), ("INTERVIEW", 6)],
        "activities": [
            (
                "OUTREACH",
                19,
                "Messaged the hiring manager on LinkedIn before applying.",
            ),
            (
                "INTERVIEW",
                6,
                "First round with the engineering manager - went well. System design round next week.",
            ),
        ],
        "jd": """Northgate AG builds logistics planning software used by carriers across Europe.
As a Senior Backend Engineer you will design and own Python services (FastAPI) on
PostgreSQL, running on AWS (ECS, RDS, SQS). You'll shape our API standards, mentor
two mid-level engineers, and own reliability for the routing platform.

Requirements: 5+ years of backend development in Python, strong SQL and data
modelling, experience with AWS and infrastructure as code (Terraform), CI/CD.
Nice to have: Kafka, event-driven architectures, Go.
English is our working language; German is a plus.
Hybrid: 2 days per week in our Zurich office. Salary CHF 120'000 - 140'000.""",
    },
    {
        "company": "Alpenblick Systems GmbH",
        "role_title": "Backend Developer Python/Django",
        "location": "Bern",
        "salary_range": None,
        "created_days_ago": 16,
        "history": [("APPLIED", 14)],
        "activities": [],
        "followup_context": None,
        "jd": """Alpenblick Systems GmbH develops booking software for Swiss tourism operators.
We are looking for a Backend Developer to extend our Django platform: REST APIs,
Celery background jobs, PostgreSQL, and integrations with payment providers.

You bring 3+ years with Python and Django, good knowledge of SQL, Docker, and
automated testing (pytest). Experience with Redis and Celery is an advantage.
Gute Deutschkenntnisse sind von Vorteil; our team works in English.
Hybrid in Bern (3 days on site). Attractive salary and 5 weeks vacation.""",
    },
    {
        "company": "Lindwurm Data AG",
        "role_title": "Data Platform Engineer",
        "location": "Basel",
        "salary_range": "CHF 110'000 - 125'000",
        "created_days_ago": 5,
        "history": [("APPLIED", 4)],
        "activities": [],
        "jd": """Lindwurm Data AG provides analytics for the life sciences industry. Our Data
Platform team builds the pipelines that move clinical-trial data into our warehouse.

You will build batch and streaming pipelines in Python and SQL, orchestrate them with
Airflow, and run them on AWS (S3, Glue, Redshift) using Terraform. You'll work closely
with data scientists on data quality.

Must have: 3+ years Python, advanced SQL, a cloud data stack (AWS preferred).
Nice to have: Spark, dbt, Kafka. English required.
Basel office, 40% remote possible. CHF 110'000 - 125'000.""",
    },
    {
        "company": "Seetal Payments AG",
        "role_title": "Senior Software Engineer, Payments",
        "location": "Zug",
        "salary_range": "CHF 130'000 - 150'000",
        "created_days_ago": 34,
        "history": [("APPLIED", 30), ("INTERVIEW", 20), ("OFFER", 3)],
        "activities": [
            (
                "INTERVIEW",
                20,
                "Technical interview: live coding (idempotent payment API) + system design.",
            ),
            (
                "INTERVIEW",
                11,
                "Final round with CTO and team. Culture fit, on-call expectations.",
            ),
            ("OFFER", 3, "Offer: CHF 138k + 10% bonus. Decision needed by Friday."),
        ],
        "jd": """Seetal Payments AG processes card and account-to-account payments for Swiss
merchants. Join the Core Payments team as a Senior Software Engineer.

You'll build high-availability Python services (FastAPI, asyncio) on PostgreSQL and
Kafka, deployed to Kubernetes on AWS. Correctness matters: idempotency, exactly-once
processing, reconciliation. You'll take part in a shared on-call rotation.

Requirements: 5+ years building production backend systems, Python, PostgreSQL,
experience with distributed systems and message queues. Payments/fintech experience
is a plus. English required.
Zug office, hybrid (2 days on site). CHF 130'000 - 150'000 plus bonus.""",
    },
    {
        "company": "Brunnmatt Health GmbH",
        "role_title": "Python Developer (Medizinsoftware)",
        "location": "Lucerne",
        "salary_range": None,
        "created_days_ago": 2,
        "history": [],
        "activities": [
            (
                "NOTE",
                2,
                "German requirement looks strict - worth asking whether English works for the team.",
            ),
        ],
        "jd": """Brunnmatt Health GmbH entwickelt Software für Arztpraxen in der Zentralschweiz.
Für unser Backend-Team suchen wir einen Python Developer (80-100%).

Ihre Aufgaben: Weiterentwicklung unserer Django-Anwendung, Schnittstellen zu
Laborsystemen (HL7/FHIR), Betreuung der PostgreSQL-Datenbanken.
Ihr Profil: abgeschlossenes Informatikstudium, 3+ Jahre Erfahrung mit Python,
Erfahrung im Gesundheitswesen von Vorteil.
Fliessende Deutschkenntnisse in Wort und Schrift sind zwingend erforderlich.
Arbeitsort Luzern, 1 Tag Homeoffice pro Woche.""",
    },
    {
        "company": "Föhnwerk Energy AG",
        "role_title": "Cloud Engineer (AWS)",
        "location": "Zurich",
        "salary_range": "CHF 115'000 - 130'000",
        "created_days_ago": 28,
        "history": [("APPLIED", 25), ("REJECTED", 10)],
        "activities": [
            (
                "REJECTION",
                10,
                "Went with a candidate with more Kubernetes production experience.",
            ),
        ],
        "jd": """Föhnwerk Energy AG runs software for solar and battery installations. Our
platform team is hiring a Cloud Engineer to own our AWS infrastructure.

You'll manage EKS clusters, build Terraform modules, run our observability stack
(Prometheus, Grafana), and improve CI/CD in GitHub Actions. Some Python tooling.

Requirements: 3+ years running production workloads on AWS, Kubernetes in
production, Terraform, Linux. Nice to have: Python, Helm, ArgoCD.
English required, German nice to have. Zurich, hybrid. CHF 115'000 - 130'000.""",
    },
    {
        "company": "Kestrel Insurance Tech AG",
        "role_title": "Staff Engineer",
        "location": "Zurich",
        "salary_range": None,
        "created_days_ago": 3,
        "history": [],
        "activities": [],
        "jd": """Kestrel Insurance Tech AG modernises claims processing for Swiss insurers. We're
hiring a Staff Engineer to set the technical direction across four product teams.

You will lead architecture for our move from a Java monolith to services, define
engineering standards, and mentor senior engineers. Our stack: Java/Kotlin, Spring
Boot, PostgreSQL, Kafka, Azure.

You have 10+ years of software engineering experience, including several years in a
staff or principal role, deep JVM expertise and experience leading large migrations.
Very good German and English. Zurich office, 3 days on site.""",
    },
    {
        "company": "Mattenhof Labs",
        "role_title": "Full-Stack Engineer",
        "location": "Remote (Switzerland)",
        "salary_range": "CHF 100'000 - 115'000",
        "created_days_ago": 45,
        "history": [("APPLIED", 40), ("GHOSTED", 5)],
        "activities": [
            ("FOLLOW_UP", 26, "Sent a short follow-up email to the recruiter."),
        ],
        "jd": """Mattenhof Labs is a 15-person startup building scheduling tools for clinics.
We need a Full-Stack Engineer who is happy anywhere in the stack.

Frontend: React, TypeScript, Next.js. Backend: Node.js and some Python services,
PostgreSQL, deployed on Vercel and AWS. You'll ship features end to end.

3+ years of full-stack experience, strong TypeScript and React, comfortable with
SQL. Startup experience is a plus. Fully remote within Switzerland, English team.
CHF 100'000 - 115'000 plus ESOP.""",
    },
    {
        "company": "Glärnisch Robotics AG",
        "role_title": "Software Engineer, Robotics Backend",
        "location": "Winterthur",
        "salary_range": None,
        "created_days_ago": 1,
        "history": [],
        "activities": [],
        # No JD: shows the manual "paste a posting to analyze" flow.
        "jd": None,
    },
    {
        "company": "Vireo Mobility AG",
        "role_title": "Backend Engineer",
        "location": "Lausanne",
        "salary_range": "CHF 105'000 - 120'000",
        "created_days_ago": 11,
        "history": [("APPLIED", 9)],
        "activities": [],
        "jd": """Vireo Mobility AG operates e-bike sharing in Romandie. Our backend team builds
the fleet and rider APIs.

Stack: Python (FastAPI) and Go microservices, PostgreSQL/PostGIS, Redis, GCP.
You'll work on pricing, trip billing and real-time fleet tracking.

Requirements: 4+ years backend development, Python or Go, SQL, REST API design.
Geospatial experience is a plus. French and English required - the office language
is French. Lausanne, hybrid. CHF 105'000 - 120'000.""",
    },
    {
        "company": "Ahornweg Software GmbH",
        "role_title": "Junior Python Developer",
        "location": "St. Gallen",
        "salary_range": "CHF 75'000 - 85'000",
        "created_days_ago": 20,
        "history": [("APPLIED", 18), ("WITHDRAWN", 12)],
        "activities": [
            (
                "NOTE",
                12,
                "Withdrew - role is clearly junior and the salary band is well below my floor.",
            ),
        ],
        "jd": """Ahornweg Software GmbH builds ERP add-ons for small manufacturers. We're looking
for a Junior Python Developer to join our team of six.

You'll write Python scripts and small Flask services, maintain SQL reports, and help
customers with data imports. Training provided.

0-2 years experience, a degree or apprenticeship in IT, basic Python and SQL.
German required (customer contact). St. Gallen office. CHF 75'000 - 85'000.""",
    },
    {
        "company": "Zinnober Media AG",
        "role_title": "Platform Engineer",
        "location": "Zurich",
        "salary_range": "CHF 120'000 - 135'000",
        "created_days_ago": 26,
        "history": [("APPLIED", 22), ("INTERVIEW", 9)],
        "activities": [
            (
                "INTERVIEW",
                9,
                "Call with the platform lead. Waiting to hear about the take-home.",
            ),
        ],
        "jd": """Zinnober Media AG runs streaming and news platforms for Swiss publishers. The
Platform team gives 60 developers a paved road to production.

You'll build our internal developer platform: Kubernetes (EKS), Terraform, GitHub
Actions pipelines, and Python tooling for service scaffolding. You'll also own
cost and reliability dashboards.

Requirements: 4+ years in platform/DevOps or backend roles, Kubernetes, Terraform,
AWS, Python or Go for tooling. English required. Zurich, hybrid.
CHF 120'000 - 135'000.""",
    },
]


def main() -> None:
    llm = get_llm_provider()
    profile = Profile(**PROFILE)
    out_apps = []

    for spec in APPLICATIONS:
        print(f"- {spec['company']}")
        entry = {k: v for k, v in spec.items() if k not in ("jd", "followup_context")}
        entry["history"] = [list(h) for h in spec["history"]]
        entry["activities"] = [list(a) for a in spec["activities"]]
        entry["parsed_jd"] = entry["match_score"] = entry["match_details"] = None
        entry["generated_followup"] = None

        if spec["jd"]:
            parsed = parse_job_description(llm, jd_text=spec["jd"])
            details = score_application_match(
                llm,
                profile=profile,
                parsed_jd=parsed,
                application_location=spec["location"],
            )
            entry["parsed_jd"] = parsed.model_dump(mode="json")
            entry["match_score"] = details.rule_score
            entry["match_details"] = details.model_dump(mode="json")

        if "followup_context" in spec:
            stage = ApplicationStage(spec["history"][-1][0])
            email = generate_followup_email(
                llm,
                company=spec["company"],
                role_title=spec["role_title"],
                stage=stage,
                context=spec["followup_context"],
            )
            entry["generated_followup"] = email.model_dump(mode="json")

        out_apps.append(entry)

    OUT.write_text(
        json.dumps(
            {"profile": PROFILE, "applications": out_apps}, indent=2, ensure_ascii=False
        )
        + "\n"
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
