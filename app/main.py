from fastapi import FastAPI
from fastapi.responses import Response

from app.config import get_settings
from app.routers import dashboard, ingest, profiles, reports

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(dashboard.router)
app.include_router(ingest.router)
app.include_router(profiles.router)
app.include_router(reports.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
