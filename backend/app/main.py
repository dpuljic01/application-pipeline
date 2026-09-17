import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.domain.errors import (
    CompanyHasApplications,
    DomainError,
    FollowUpGenerationError,
    Forbidden,
    InvalidTransition,
    JDNotParsed,
    JDParseError,
    MatchingError,
    NotFound,
)

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Dossier API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")


# Defense-in-depth, not the primary error-handling path: every route already
# catches and maps its own domain errors explicitly (see CLAUDE.md's "Domain
# Errors -> HTTP Status Codes" table) - these two handlers only fire if a
# route forgets to, so a missed except block degrades to a sensible status
# code instead of a raw, unhandled 500 with no detail.
_DOMAIN_ERROR_STATUS: dict[type[DomainError], int] = {
    NotFound: 404,
    Forbidden: 403,
    InvalidTransition: 409,
    CompanyHasApplications: 409,
    JDParseError: 502,
    JDNotParsed: 409,
    MatchingError: 502,
    FollowUpGenerationError: 502,
}


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = _DOMAIN_ERROR_STATUS.get(type(exc), 500)
    logger.warning(
        "%s reached the global handler (route should map it explicitly) on %s %s",
        type(exc).__name__,
        request.method,
        request.url.path,
    )
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
