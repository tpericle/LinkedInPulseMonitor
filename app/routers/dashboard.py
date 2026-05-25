from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apify_http import ApifyHttpClient
from app.config import get_settings
from app.db import get_db
from app.manual_fetch import (
    DEFAULT_LIMIT_PER_SOURCE,
    GuardedFetchError,
    ManualFetchResult,
    run_manual_apify_fetch,
)
from app.models import DailyReport, Person, Post, ScrapeRun
from app.people import add_tracked_profile
from app.reports import generate_daily_report

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_dashboard_context(request, db),
    )


@router.get("/dashboard/profiles")
def dashboard_profiles_redirect() -> RedirectResponse:
    return RedirectResponse(url="/dashboard#profile-administration", status_code=303)


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
    return _admin_redirect(f"Added {display_name} to active profiles")


@router.post("/dashboard/profiles/{person_id}/archive")
def archive_dashboard_profile(
    person_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    person = db.get(Person, person_id)
    if person is None:
        return RedirectResponse(url="/dashboard?success=Profile not found", status_code=303)

    person.is_active = False
    db.commit()
    display_name = person.full_name or person.linkedin_url
    return _admin_redirect(
        f"Archived {display_name}. They will not be included in future fetches."
    )


@router.post("/dashboard/profiles/{person_id}/reactivate")
def reactivate_dashboard_profile(
    person_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    person = db.get(Person, person_id)
    if person is None:
        return RedirectResponse(url="/dashboard?success=Profile not found", status_code=303)

    person.is_active = True
    db.commit()
    display_name = person.full_name or person.linkedin_url
    return _admin_redirect(
        f"Reactivated {display_name}. They will be included in future fetches."
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


@router.post("/dashboard/fetch/apify")
def fetch_latest_apify_posts(db: Annotated[Session, Depends(get_db)]) -> RedirectResponse:
    try:
        result = _run_dashboard_manual_fetch(db)
    except GuardedFetchError as error:
        return RedirectResponse(url=f"/dashboard?success={quote(str(error))}", status_code=303)

    query_string = urlencode(
        {"success": "Fetch recap", "log": _build_fetch_log(result)},
        doseq=True,
    )
    return RedirectResponse(url=f"/dashboard?{query_string}", status_code=303)


def _run_dashboard_manual_fetch(db: Session) -> ManualFetchResult:
    settings = get_settings()
    if not settings.apify_token or not settings.apify_actor_id:
        raise GuardedFetchError("Missing APIFY_TOKEN or APIFY_ACTOR_ID in environment/.env.")

    with ApifyHttpClient(token=settings.apify_token) as client:
        return run_manual_apify_fetch(db, client=client, actor_id=settings.apify_actor_id)


def _admin_redirect(message: str) -> RedirectResponse:
    query_string = urlencode({"success": message})
    return RedirectResponse(
        url=f"/dashboard?{query_string}#profile-administration",
        status_code=303,
    )


def _blank_to_none(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _is_linkedin_profile_url(value: str) -> bool:
    return value.startswith("https://www.linkedin.com/in/")


def _dashboard_context(
    request: Request,
    db: Session,
    *,
    form_error: str | None = None,
) -> dict[str, object]:
    settings = get_settings()
    recent_cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
    active_profiles = db.scalars(
        select(Person).where(Person.is_active.is_(True)).order_by(Person.added_at.desc()).limit(10)
    ).all()
    archived_profiles = db.scalars(
        select(Person).where(Person.is_active.is_(False)).order_by(Person.added_at.desc()).limit(10)
    ).all()
    recent_posts = db.scalars(
        select(Post)
        .where(Post.authored_at.is_not(None), Post.authored_at >= recent_cutoff)
        .order_by(Post.authored_at.desc())
        .limit(10)
    ).all()
    latest_report = db.scalar(select(DailyReport).order_by(DailyReport.report_date.desc()).limit(1))
    latest_fetch = db.scalar(
        select(ScrapeRun)
        .where(ScrapeRun.provider == "apify")
        .order_by(ScrapeRun.finished_at.desc().nullslast(), ScrapeRun.started_at.desc().nullslast())
        .limit(1)
    )
    latest_fetch_at = None
    if latest_fetch:
        latest_fetch_at = latest_fetch.finished_at or latest_fetch.started_at

    return {
        "app_name": settings.app_name,
        "active_profiles": active_profiles,
        "active_profile_count": len(active_profiles),
        "archived_profiles": archived_profiles,
        "archived_profile_count": len(archived_profiles),
        "recent_posts": recent_posts,
        "recent_post_cards": [_post_card(post) for post in recent_posts],
        "recent_post_days": 7,
        "latest_fetch_at": latest_fetch_at,
        "latest_fetch_display": _format_datetime(latest_fetch_at),
        "latest_report": latest_report,
        "success_message": request.query_params.get("success"),
        "fetch_log": request.query_params.getlist("log"),
        "form_error": form_error,
    }


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M")


def _post_card(post: Post) -> dict[str, object]:
    return {
        "author_name": post.author_name or "Unknown author",
        "linkedin_url": post.linkedin_url,
        "authored_at": post.authored_at,
        "authored_at_display": _format_datetime(post.authored_at),
        "age_display": _format_age(post.authored_at),
        "review_label": _review_label(post.authored_at),
        "summary": _post_hook_summary(post.content),
    }


def _format_age(value: datetime | None) -> str | None:
    if value is None:
        return None
    now = datetime.now(UTC).replace(tzinfo=None)
    elapsed_seconds = max(0, int((now - value).total_seconds()))
    elapsed_minutes = elapsed_seconds // 60
    if elapsed_minutes < 60:
        return f"~{max(1, elapsed_minutes)}m ago"
    elapsed_hours = elapsed_minutes // 60
    if elapsed_hours < 48:
        return f"~{elapsed_hours}h ago"
    elapsed_days = elapsed_hours // 24
    return f"~{elapsed_days}d ago"


def _review_label(value: datetime | None) -> str:
    if value is None:
        return "Review window"
    now = datetime.now(UTC).replace(tzinfo=None)
    if now - value <= timedelta(hours=24):
        return "Review today"
    return "Review window"


def _post_hook_summary(content: str) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if lines:
        return "\n".join(lines[:3])
    words = content.strip().split()
    if len(words) <= 45:
        return content.strip()
    return " ".join(words[:45]) + "…"


def _build_fetch_log(result: ManualFetchResult) -> list[str]:
    profile_word = "profile" if result.profiles_checked == 1 else "profiles"
    cost = "cost unavailable" if result.usage_total_usd is None else f"${result.usage_total_usd}"
    return [
        f"Found {result.profiles_checked} active {profile_word}.",
        f"Asked Apify for up to {DEFAULT_LIMIT_PER_SOURCE} latest posts per profile.",
        f"Apify returned {result.items_returned} items.",
        f"Parsed {result.parsed_count} posts from those items.",
        (
            f"Saved {result.inserted_count} new post"
            f"{'' if result.inserted_count == 1 else 's'} and skipped "
            f"{result.skipped_count} existing or out-of-window posts."
        ),
        f"Provider status: {result.status}.",
        f"Estimated Apify cost: {cost}.",
    ]


def _dashboard_response(
    request: Request,
    db: Session,
    *,
    status_code: int = 200,
    form_error: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_dashboard_context(request, db, form_error=form_error),
        status_code=status_code,
    )


def _parse_tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split(",") if tag.strip()]
