from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apify_http import ApifyHttpClient
from app.commentary_profile import build_comment_starter_ideas, load_commentary_profile
from app.config import get_settings
from app.db import get_db
from app.manual_fetch import (
    DEFAULT_LIMIT_PER_SOURCE,
    DEFAULT_MAX_PROFILES,
    DEFAULT_MAX_TOTAL_CHARGE_USD,
    GuardedFetchError,
    ManualFetchResult,
    run_manual_apify_fetch,
)
from app.models import DailyReport, Person, Post, ScrapeRun
from app.people import add_tracked_profile
from app.reports import generate_daily_report

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

NORMAL_FETCH_LOOKBACK = timedelta(hours=24)
NEW_PROFILE_FETCH_LOOKBACK = timedelta(days=7)


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

    if not _is_linkedin_profile_url(linkedin_url):
        return _dashboard_response(
            request,
            db,
            status_code=400,
            form_error="Please enter a LinkedIn profile URL that starts with https://www.linkedin.com/in/.",
        )

    existing = _find_person_by_canonical_url(db, _canonical_linkedin_url(linkedin_url))
    will_add_active = existing is None or not existing.is_active
    if will_add_active and _active_profile_count(db) >= DEFAULT_MAX_PROFILES:
        return _dashboard_response(
            request,
            db,
            status_code=400,
            form_error=(
                f"You can have no more than {DEFAULT_MAX_PROFILES} active profiles. "
                "Pause tracking for someone before adding another active profile."
            ),
        )

    person = add_tracked_profile(
        db,
        linkedin_url=linkedin_url,
        full_name=full_name,
    )
    person.company = None
    person.tags_json = None
    db.commit()
    db.refresh(person)
    display_name = person.full_name or person.linkedin_url
    return _admin_redirect(
        f"Added {display_name} to active profiles. "
        "This profile will be included in your next fetch."
    )


@router.post("/dashboard/profiles/{person_id}/edit", response_model=None)
async def edit_dashboard_profile(
    person_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse | RedirectResponse:
    person = db.get(Person, person_id)
    if person is None:
        return _admin_redirect("Profile not found")

    form = await request.form()
    linkedin_url = str(form.get("linkedin_url", "")).strip()
    full_name = _blank_to_none(str(form.get("full_name", "")))
    if not _is_linkedin_profile_url(linkedin_url):
        return _dashboard_response(
            request,
            db,
            status_code=400,
            form_error="Please enter a LinkedIn profile URL that starts with https://www.linkedin.com/in/.",
        )

    canonical_url = _canonical_linkedin_url(linkedin_url)
    duplicate = _find_person_by_canonical_url(db, canonical_url)
    if duplicate is not None and duplicate.id != person.id:
        return _dashboard_response(
            request,
            db,
            status_code=400,
            form_error="Another profile already uses that LinkedIn URL.",
        )

    person.full_name = full_name
    person.linkedin_url = canonical_url
    db.commit()
    display_name = person.full_name or person.linkedin_url
    return _admin_redirect(f"Updated {display_name}.")


@router.post("/dashboard/profiles/{person_id}/pause")
def pause_dashboard_profile(
    person_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    person = db.get(Person, person_id)
    if person is None:
        return _admin_redirect("Profile not found")

    person.is_active = False
    db.commit()
    display_name = person.full_name or person.linkedin_url
    return _admin_redirect(
        f"Paused tracking for {display_name}. They will not be included in future fetches."
    )


@router.post("/dashboard/profiles/{person_id}/archive")
def archive_dashboard_profile_legacy(
    person_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    return pause_dashboard_profile(person_id, db)


@router.post("/dashboard/profiles/{person_id}/reactivate")
def reactivate_dashboard_profile(
    person_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    person = db.get(Person, person_id)
    if person is None:
        return _admin_redirect("Profile not found")
    if not person.is_active and _active_profile_count(db) >= DEFAULT_MAX_PROFILES:
        return _admin_redirect(
            f"You can have no more than {DEFAULT_MAX_PROFILES} active profiles. "
            "Pause tracking for someone before reactivating another profile."
        )

    person.is_active = True
    db.commit()
    display_name = person.full_name or person.linkedin_url
    return _admin_redirect(
        f"Reactivated {display_name}. They will be included in future fetches."
    )


@router.post("/dashboard/profiles/{person_id}/delete")
def delete_dashboard_profile(
    person_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    person = db.get(Person, person_id)
    if person is None:
        return _admin_redirect("Profile not found")
    if person.is_active:
        return _admin_redirect("Pause tracking before deleting a profile.")

    display_name = person.full_name or person.linkedin_url
    for post in db.scalars(select(Post).where(Post.person_id == person.id)).all():
        post.person_id = None
    db.delete(person)
    db.commit()
    return _admin_redirect(f"Deleted {display_name}. Historical posts were kept.")


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


@router.get("/dashboard/fetch/apify", response_class=HTMLResponse)
def confirm_latest_apify_posts(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_dashboard_context(request, db, show_fetch_confirmation=True),
    )


@router.post("/dashboard/fetch/apify/execute")
def fetch_latest_apify_posts(db: Annotated[Session, Depends(get_db)]) -> RedirectResponse:
    try:
        result = _run_dashboard_manual_fetch(db)
    except GuardedFetchError as error:
        return RedirectResponse(url=f"/dashboard?success={quote(str(error))}", status_code=303)

    query_string = urlencode(
        {"success": "Fetch complete", "log": _build_fetch_log(result)},
        doseq=True,
    )
    return RedirectResponse(url=f"/dashboard?{query_string}", status_code=303)


@router.post("/dashboard/fetch/apify")
def fetch_latest_apify_posts_legacy(db: Annotated[Session, Depends(get_db)]) -> RedirectResponse:
    return fetch_latest_apify_posts(db)


def _run_dashboard_manual_fetch(db: Session) -> ManualFetchResult:
    settings = get_settings()
    if not settings.apify_token or not settings.apify_actor_id:
        raise GuardedFetchError("Missing APIFY_TOKEN or APIFY_ACTOR_ID in environment/.env.")

    active_profiles = _active_profiles(db)
    if not active_profiles:
        raise GuardedFetchError("Refusing to run: no active profiles are configured.")
    if len(active_profiles) > DEFAULT_MAX_PROFILES:
        raise GuardedFetchError(
            f"Refusing to run: {len(active_profiles)} active profiles exceeds "
            f"max_profiles={DEFAULT_MAX_PROFILES}."
        )

    latest_success = _latest_successful_fetch_at(db)
    existing_profiles, new_profiles = _partition_profiles_by_fetch_history(
        active_profiles, latest_success
    )

    results: list[ManualFetchResult] = []
    with ApifyHttpClient(token=settings.apify_token) as client:
        if existing_profiles:
            results.append(
                run_manual_apify_fetch(
                    db,
                    client=client,
                    actor_id=settings.apify_actor_id,
                    profiles=existing_profiles,
                    lookback=NORMAL_FETCH_LOOKBACK,
                )
            )
        if new_profiles:
            results.append(
                run_manual_apify_fetch(
                    db,
                    client=client,
                    actor_id=settings.apify_actor_id,
                    profiles=new_profiles,
                    lookback=NEW_PROFILE_FETCH_LOOKBACK,
                )
            )

    return _combine_fetch_results(results)


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


def _canonical_linkedin_url(url: str) -> str:
    return url.strip().rstrip("/") + "/"


def _find_person_by_canonical_url(db: Session, canonical_url: str) -> Person | None:
    people = db.scalars(select(Person)).all()
    for person in people:
        if _canonical_linkedin_url(person.linkedin_url) == canonical_url:
            return person
    return None


def _active_profile_count(db: Session) -> int:
    return len(_active_profiles(db))


def _active_profiles(db: Session) -> list[Person]:
    return list(
        db.scalars(
            select(Person).where(Person.is_active.is_(True)).order_by(Person.added_at.asc())
        ).all()
    )


def _latest_successful_fetch_at(db: Session) -> datetime | None:
    latest_fetch = db.scalar(
        select(ScrapeRun)
        .where(ScrapeRun.provider == "apify", ScrapeRun.status == "SUCCEEDED")
        .order_by(ScrapeRun.finished_at.desc().nullslast(), ScrapeRun.started_at.desc().nullslast())
        .limit(1)
    )
    if latest_fetch is None:
        return None
    return latest_fetch.finished_at or latest_fetch.started_at


def _partition_profiles_by_fetch_history(
    profiles: list[Person], latest_success: datetime | None
) -> tuple[list[Person], list[Person]]:
    if latest_success is None:
        return [], profiles
    existing_profiles = []
    new_profiles = []
    for profile in profiles:
        if profile.added_at and profile.added_at <= latest_success:
            existing_profiles.append(profile)
        else:
            new_profiles.append(profile)
    return existing_profiles, new_profiles


def _dashboard_context(
    request: Request,
    db: Session,
    *,
    form_error: str | None = None,
    show_fetch_confirmation: bool = False,
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
        .limit(25)
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

    latest_success = _latest_successful_fetch_at(db)
    existing_profiles, new_profiles = _partition_profiles_by_fetch_history(
        list(active_profiles), latest_success
    )
    commentary_profile = load_commentary_profile()
    recent_post_cards = [_post_card(post, commentary_profile) for post in recent_posts]
    visible_recent_post_cards = recent_post_cards[:5]
    extra_recent_post_cards = recent_post_cards[5:]

    return {
        "app_name": settings.app_name,
        "active_profiles": active_profiles,
        "active_profile_count": len(active_profiles),
        "active_profile_limit": DEFAULT_MAX_PROFILES,
        "archived_profiles": archived_profiles,
        "archived_profile_count": len(archived_profiles),
        "recent_posts": recent_posts,
        "recent_post_cards": recent_post_cards,
        "visible_recent_post_cards": visible_recent_post_cards,
        "extra_recent_post_cards": extra_recent_post_cards,
        "extra_recent_post_count": len(extra_recent_post_cards),
        "recent_post_days": 7,
        "normal_fetch_hours": 24,
        "new_profile_fetch_days": 7,
        "limit_per_source": DEFAULT_LIMIT_PER_SOURCE,
        "max_total_charge_usd": DEFAULT_MAX_TOTAL_CHARGE_USD,
        "latest_fetch_at": latest_fetch_at,
        "latest_fetch_display": _format_datetime(latest_fetch_at),
        "latest_report": latest_report,
        "success_message": request.query_params.get("success"),
        "fetch_log": request.query_params.getlist("log"),
        "form_error": form_error,
        "show_fetch_confirmation": show_fetch_confirmation,
        "fetch_existing_profiles": existing_profiles,
        "fetch_new_profiles": new_profiles,
    }


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M")


def _post_card(post: Post, commentary_profile) -> dict[str, object]:
    return {
        "author_name": post.author_name or "Unknown author",
        "linkedin_url": post.linkedin_url,
        "authored_at": post.authored_at,
        "authored_at_display": _format_datetime(post.authored_at),
        "age_display": _format_age(post.authored_at),
        "review_label": _review_label(post.authored_at),
        "summary": _post_hook_summary(post.content),
        "comment_starters": build_comment_starter_ideas(post.content, commentary_profile),
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


def _combine_fetch_results(results: list[ManualFetchResult]) -> ManualFetchResult:
    if not results:
        raise GuardedFetchError("Refusing to run: no active profiles are configured.")
    usage_values = [
        result.usage_total_usd for result in results if result.usage_total_usd is not None
    ]
    usage_total = sum(usage_values) if usage_values else None
    return ManualFetchResult(
        profiles_checked=sum(result.profiles_checked for result in results),
        items_returned=sum(result.items_returned for result in results),
        parsed_count=sum(result.parsed_count for result in results),
        inserted_count=sum(result.inserted_count for result in results),
        skipped_count=sum(result.skipped_count for result in results),
        provider_run_id=", ".join(
            result.provider_run_id for result in results if result.provider_run_id
        ) or None,
        provider_dataset_id=", ".join(
            result.provider_dataset_id for result in results if result.provider_dataset_id
        ) or None,
        status=(
            "SUCCEEDED"
            if all(result.status == "SUCCEEDED" for result in results)
            else "PARTIAL"
        ),
        usage_total_usd=usage_total,
        charged_event_counts=None,
    )


def _build_fetch_log(result: ManualFetchResult) -> list[str]:
    profile_word = "profile" if result.profiles_checked == 1 else "profiles"
    cost = "cost unavailable" if result.usage_total_usd is None else f"${result.usage_total_usd}"
    saved_line = (
        f"Saved {result.inserted_count} new post"
        f"{'' if result.inserted_count == 1 else 's'} and skipped "
        f"{result.skipped_count} item"
        f"{'' if result.skipped_count == 1 else 's'}."
    )
    if result.inserted_count == 0:
        saved_line += " No new saved posts is a normal outcome when nothing recent is found."
    return [
        f"Checked {result.profiles_checked} active {profile_word}.",
        f"Asked Apify for up to {DEFAULT_LIMIT_PER_SOURCE} latest posts per profile.",
        f"Apify returned {result.items_returned} items.",
        f"Parsed {result.parsed_count} posts from those items.",
        saved_line,
        "Skipped posts may be duplicates, outside the lookback window, or unparseable.",
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
