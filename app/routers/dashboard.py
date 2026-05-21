from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import DailyReport, Person, Post

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    settings = get_settings()
    tracked_profiles = db.scalars(select(Person).order_by(Person.added_at.desc()).limit(5)).all()
    recent_posts = db.scalars(select(Post).order_by(Post.authored_at.desc()).limit(5)).all()
    latest_report = db.scalar(select(DailyReport).order_by(DailyReport.report_date.desc()).limit(1))
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "app_name": settings.app_name,
            "tracked_profiles": tracked_profiles,
            "recent_posts": recent_posts,
            "latest_report": latest_report,
        },
    )
