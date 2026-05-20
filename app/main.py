from fastapi import FastAPI

from app.config import get_settings
from app.routers import dashboard

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
