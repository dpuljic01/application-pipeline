from fastapi import FastAPI
from app.api.routes.applications import router as applications_router
from app.api.routes.activities import router as activities_router
from app.api.routes.health import router as health_router


app = FastAPI(title="Application Pipeline API")
app.include_router(applications_router)
app.include_router(activities_router)
app.include_router(health_router)
