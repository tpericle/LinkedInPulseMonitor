from fastapi import FastAPI

from app.config import get_settings
from app.routers import dashboard, ingest, profiles, reports

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(dashboard.router)
app.include_router(ingest.router)
app.include_router(profiles.router)
app.include_router(reports.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
