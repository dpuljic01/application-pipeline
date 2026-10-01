"""POST /profile/extract-from-cv: PDF or pasted text in, suggested profile
fields out, nothing saved."""

import json
from decimal import Decimal

from sqlalchemy import select

from app.api.deps import get_llm_provider
from app.db.models.llm_usage import LLMUsage
from app.integrations.llm.base import LLMProviderError, LLMResponse

URL = "/api/profile/extract-from-cv"

EXTRACTION = {
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "years_experience": 6,
    "languages": [{"language": "English", "level": "Fluent (C2)"}],
    "seniority": "senior",
}


class RecordingLLM:
    name = "gemini"

    def __init__(self, *, content: str = json.dumps(EXTRACTION), fail=False):
        self.content = content
        self.fail = fail
        self.user_prompts: list[str] = []

    def complete(self, *, user_prompt, **kwargs) -> LLMResponse:
        self.user_prompts.append(user_prompt)
        if self.fail:
            raise LLMProviderError("simulated provider failure")
        return LLMResponse(
            content=self.content,
            provider="gemini",
            model="cv-test-model",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            cost_usd=Decimal("0"),
            latency_ms=1,
        )


def _use(client, llm: RecordingLLM) -> RecordingLLM:
    client.app.dependency_overrides[get_llm_provider] = lambda: llm
    return llm


def make_pdf(text: str | None) -> bytes:
    """Smallest valid single-page PDF; text=None gives a page with no text
    layer, like a scanned CV."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode() if text else b""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF\n" % xref_at
    return out


def test_pasted_text_returns_suggestion_without_saving(client):
    llm = _use(client, RecordingLLM())

    response = client.post(
        URL, data={"text": "Jane Doe - Backend engineer at Northgate AG"}
    )

    assert response.status_code == 200, response.text
    assert response.json() == EXTRACTION
    assert "Northgate AG" in llm.user_prompts[0]
    # So "2021 - present" can be turned into years of experience.
    assert llm.user_prompts[0].startswith("Today's date: ")
    assert client.get("/api/profile").json()["skills"] == []


def test_pdf_text_layer_reaches_the_llm(client):
    llm = _use(client, RecordingLLM())

    response = client.post(
        URL,
        files={
            "file": (
                "cv.pdf",
                make_pdf("Backend engineer at Northgate AG"),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200, response.text
    assert "Northgate AG" in llm.user_prompts[0]


def test_pdf_without_text_layer_is_rejected_before_any_llm_call(client):
    llm = _use(client, RecordingLLM())

    response = client.post(
        URL, files={"file": ("scan.pdf", make_pdf(None), "application/pdf")}
    )

    assert response.status_code == 422
    assert "scanned" in response.json()["detail"]
    assert llm.user_prompts == []


def test_non_pdf_file_is_415(client):
    _use(client, RecordingLLM())
    response = client.post(
        URL,
        files={
            "file": ("cv.docx", b"PK\x03\x04 not a pdf", "application/octet-stream")
        },
    )
    assert response.status_code == 415


def test_oversized_file_is_413(client):
    _use(client, RecordingLLM())
    big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024)
    response = client.post(URL, files={"file": ("cv.pdf", big, "application/pdf")})
    assert response.status_code == 413


def test_needs_exactly_one_of_file_or_text(client):
    _use(client, RecordingLLM())
    assert client.post(URL, data={"text": "  "}).status_code == 422
    both = client.post(
        URL,
        data={"text": "some cv"},
        files={"file": ("cv.pdf", make_pdf("x"), "application/pdf")},
    )
    assert both.status_code == 422


def test_llm_failure_is_502(client):
    _use(client, RecordingLLM(fail=True))
    response = client.post(URL, data={"text": "Backend engineer"})
    assert response.status_code == 502


def test_invalid_language_level_is_502(client):
    bad = {**EXTRACTION, "languages": [{"language": "German", "level": "pretty good"}]}
    _use(client, RecordingLLM(content=json.dumps(bad)))
    response = client.post(URL, data={"text": "Backend engineer"})
    assert response.status_code == 502


def test_call_is_logged_as_cv_extract(client, db_session):
    _use(client, RecordingLLM())
    client.post(URL, data={"text": "Backend engineer"})

    rows = db_session.scalars(
        select(LLMUsage).where(
            LLMUsage.operation == "cv_extract", LLMUsage.model == "cv-test-model"
        )
    ).all()
    assert len(rows) == 1
