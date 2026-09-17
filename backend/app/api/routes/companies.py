from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_company_service
from app.api.schemas.application import ApplicationRead
from app.api.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.core.security.deps import CurrentUser, get_current_user
from app.db.models.application import Application
from app.db.models.company import Company
from app.domain.errors import CompanyHasApplications, NotFound
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead)
async def create_company(
    payload: CompanyCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> Company:
    return service.create_company(
        user_id=current_user.user_id,
        name=payload.name,
        website=str(payload.website) if payload.website else None,
        industry=payload.industry,
        size=payload.size,
        location=payload.location,
        notes=payload.notes,
    )


@router.get("", response_model=list[CompanyRead])
async def list_companies(
    search: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> list[Company]:
    return service.list_companies_for_user(user_id=current_user.user_id, search=search)


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> Company:
    try:
        return service.get_company_for_user(
            user_id=current_user.user_id, company_id=company_id
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Company not found")


@router.get("/{company_id}/applications", response_model=list[ApplicationRead])
async def list_company_applications(
    company_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> list[Application]:
    try:
        return service.list_applications_for_company(
            user_id=current_user.user_id, company_id=company_id
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Company not found")


@router.put("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> Company:
    data = payload.model_dump(exclude_unset=True)
    if data.get("website") is not None:
        data["website"] = str(data["website"])
    try:
        return service.update_company(
            user_id=current_user.user_id, company_id=company_id, data=data
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Company not found")


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> None:
    try:
        service.delete_company(user_id=current_user.user_id, company_id=company_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Company not found")
    except CompanyHasApplications as e:
        raise HTTPException(status_code=409, detail=str(e))
