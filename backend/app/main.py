from fastapi import FastAPI
from app.api.routes import api_router


app = FastAPI(title="Application Pipeline API")
app.include_router(api_router, prefix="/api")
