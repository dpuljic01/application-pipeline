# app/api/routes/__init__.py
from fastapi import APIRouter
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.applications import router as applications_router
from app.api.routes.activities import router as activities_router
from app.api.routes.companies import router as companies_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(applications_router)
api_router.include_router(activities_router)
api_router.include_router(companies_router)
api_router.include_router(health_router)
