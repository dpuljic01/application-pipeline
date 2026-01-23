from fastapi import FastAPI
from app.core.config import settings
from app.db.session import test_connection

app = FastAPI(title="Application Pipeline API")

@app.get("/health")
def health_check():
    test_connection()
    return {"status": "ok"}