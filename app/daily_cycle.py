from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.apify_http import ApifyHttpClient
from app.config import get_settings
from app.manual_fetch import ManualFetchResult, run_manual_apify_fetch
from app.reports import generate_daily_report


@dataclass(frozen=True)
class DailyCycleResult:
    fetch_result: ManualFetchResult
    report_id: int


def run_dashboard_apify_fetch(db: Session) -> ManualFetchResult:
    settings = get_settings()
    if not settings.apify_token or not settings.apify_actor_id:
        from app.manual_fetch import GuardedFetchError

        raise GuardedFetchError("Missing APIFY_TOKEN or APIFY_ACTOR_ID in environment/.env.")

    with ApifyHttpClient(token=settings.apify_token) as client:
        return run_manual_apify_fetch(db, client=client, actor_id=settings.apify_actor_id)


def run_daily_cycle(db: Session, *, now: datetime | None = None) -> DailyCycleResult:
    fetch_result = run_dashboard_apify_fetch(db)
    report_result = generate_daily_report(db, now=now)
    return DailyCycleResult(fetch_result=fetch_result, report_id=report_result.report_id)


def format_daily_cycle_recap(result: DailyCycleResult) -> str:
    fetch = result.fetch_result
    cost = "unavailable" if fetch.usage_total_usd is None else f"${fetch.usage_total_usd}"
    return "\n".join(
        [
            "Daily cycle complete",
            f"profiles checked: {fetch.profiles_checked}",
            f"items returned: {fetch.items_returned}",
            f"parsed: {fetch.parsed_count}",
            f"inserted: {fetch.inserted_count}",
            f"skipped: {fetch.skipped_count}",
            f"provider status: {fetch.status}",
            f"cost: {cost}",
            f"report id: {result.report_id}",
        ]
    )
