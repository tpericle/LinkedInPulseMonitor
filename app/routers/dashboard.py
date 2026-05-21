from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import DailyReport, Person, Post
from app.people import add_tracked_profile
from app.reports import generate_daily_report

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
            "success_message": request.query_params.get("success"),
        },
    )


@router.post("/dashboard/profiles", response_model=None)
async def create_dashboard_profile(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse | RedirectResponse:
    form = await request.form()
    linkedin_url = str(form.get("linkedin_url", "")).strip()
    full_name = _blank_to_none(str(form.get("full_name", "")))
    company = _blank_to_none(str(form.get("company", "")))
    tags = _parse_tags(str(form.get("tags", "")))

    if not _is_linkedin_profile_url(linkedin_url):
        return _dashboard_response(
            request,
            db,
            status_code=400,
            form_error="Please enter a LinkedIn profile URL that starts with https://www.linkedin.com/in/.",
        )

    person = add_tracked_profile(
        db,
        linkedin_url=linkedin_url,
        full_name=full_name,
        company=company,
        tags=tags,
    )
    display_name = person.full_name or person.linkedin_url
    return RedirectResponse(
        url=f"/dashboard?success=Now following {display_name}",
        status_code=303,
    )


@router.post("/dashboard/reports/daily")
def create_dashboard_daily_report(db: Annotated[Session, Depends(get_db)]) -> RedirectResponse:
    result = generate_daily_report(db)
    report = db.get_one(DailyReport, result.report_id)
    post_word = "post" if report.post_count == 1 else "posts"
    return RedirectResponse(
        url=(
            "/dashboard?success="
            f"Generated today’s mock report from {report.post_count} recent {post_word}"
        ),
        status_code=303,
    )


def _blank_to_none(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _is_linkedin_profile_url(value: str) -> bool:
    return value.startswith("https://www.linkedin.com/in/")


def _dashboard_response(
    request: Request,
    db: Session,
    *,
    status_code: int = 200,
    form_error: str | None = None,
) -> HTMLResponse:
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
            "success_message": request.query_params.get("success"),
            "form_error": form_error,
        },
        status_code=status_code,
    )


def _parse_tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split(",") if tag.strip()]
