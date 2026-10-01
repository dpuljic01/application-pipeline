from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_profile_service, tracked_llm
from app.api.schemas.profile import ProfileRead, ProfileUpdate
from app.core.security.deps import CurrentUser, get_current_user
from app.db.models.profile import Profile
from app.domain.errors import CVExtractionError, InvalidCV, LLMBudgetExceeded
from app.integrations.llm.base import LLMProvider
from app.services.cv_extractor import (
    CVExtraction,
    extract_profile_from_cv,
    extract_text_from_pdf,
)
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])

MAX_CV_BYTES = 5 * 1024 * 1024


@router.get("", response_model=ProfileRead)
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> Profile:
    return service.get_or_create_profile_for_user(user_id=current_user.user_id)


@router.put("", response_model=ProfileRead)
async def update_profile(
    payload: ProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> Profile:
    data = payload.model_dump(exclude_unset=True)
    return service.update_profile(user_id=current_user.user_id, data=data)


# Plain `def`, not `async def`: PDF parsing and the LLM call are blocking, so
# FastAPI must run this in its threadpool. Inside `async def` they would
# stall the event loop - and every other request - for the whole LLM call.
@router.post("/extract-from-cv", response_model=CVExtraction)
def extract_from_cv(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    llm: LLMProvider = Depends(tracked_llm("cv_extract")),
) -> CVExtraction:
    """Suggests profile fields from a CV (PDF upload or pasted text). Saves
    nothing - the client fills its form with the result and the user saves
    it via PUT /profile."""
    if (file is None) == (not text or not text.strip()):
        raise HTTPException(
            status_code=422, detail="Send either a PDF file or the CV text"
        )

    try:
        if file is not None:
            data = file.file.read(MAX_CV_BYTES + 1)
            if len(data) > MAX_CV_BYTES:
                raise HTTPException(status_code=413, detail="CV must be under 5 MB")
            if not data.startswith(b"%PDF"):
                raise HTTPException(
                    status_code=415, detail="Only PDF files are supported"
                )
            cv_text = extract_text_from_pdf(data)
        else:
            cv_text = text or ""
        return extract_profile_from_cv(llm, cv_text=cv_text)
    except InvalidCV as e:
        raise HTTPException(status_code=422, detail=str(e))
    except CVExtractionError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except LLMBudgetExceeded as e:
        raise HTTPException(status_code=503, detail=str(e))
