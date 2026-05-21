from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Person, ScrapeRun
from app.pipeline import ingest_apify_items

DEFAULT_LIMIT_PER_SOURCE = 3
DEFAULT_MAX_PROFILES = 3
DEFAULT_MAX_TOTAL_CHARGE_USD = 1.0


class GuardedFetchError(ValueError):
    pass


class ApifyRunClient(Protocol):
    def run_actor(
        self,
        actor_id: str,
        actor_input: dict[str, Any],
        max_total_charge_usd: float,
    ) -> dict[str, Any]: ...

    def fetch_dataset_items(self, dataset_id: str) -> list[dict[str, Any]]: ...

    def fetch_run_details(self, run_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ManualFetchResult:
    profiles_checked: int
    items_returned: int
    parsed_count: int
    inserted_count: int
    skipped_count: int
    provider_run_id: str | None
    provider_dataset_id: str | None
    status: str
    usage_total_usd: float | None
    charged_event_counts: dict[str, Any] | None


def run_manual_apify_fetch(
    db: Session,
    *,
    client: ApifyRunClient,
    actor_id: str,
    now: datetime | None = None,
    max_profiles: int = DEFAULT_MAX_PROFILES,
    limit_per_source: int = DEFAULT_LIMIT_PER_SOURCE,
    max_total_charge_usd: float = DEFAULT_MAX_TOTAL_CHARGE_USD,
) -> ManualFetchResult:
    active_profiles = db.scalars(
        select(Person).where(Person.is_active.is_(True)).order_by(Person.added_at.asc())
    ).all()
    if len(active_profiles) > max_profiles:
        profile_count = len(active_profiles)
        raise GuardedFetchError(
            f"Refusing to run: {profile_count} active profiles exceeds "
            f"max_profiles={max_profiles}."
        )
    if not active_profiles:
        raise GuardedFetchError("Refusing to run: no active profiles are configured.")

    actor_input = {
        "deepScrape": True,
        "limitPerSource": limit_per_source,
        "rawData": False,
        "urls": [profile.linkedin_url for profile in active_profiles],
    }
    run = client.run_actor(actor_id, actor_input, max_total_charge_usd)
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise GuardedFetchError("Apify run did not return a defaultDatasetId.")

    items = client.fetch_dataset_items(str(dataset_id))
    pipeline_result = ingest_apify_items(db, items, now=now or datetime.now(UTC))

    run_id = _optional_str(run.get("id"))
    run_details = client.fetch_run_details(run_id) if run_id else {}
    status = _optional_str(run_details.get("status") or run.get("status")) or "UNKNOWN"
    scrape_run = ScrapeRun(
        provider="apify",
        provider_run_id=run_id,
        provider_dataset_id=str(dataset_id),
        status=status,
        item_count=len(items),
        raw_json=json.dumps(_safe_run_metadata(run, run_details)),
    )
    db.add(scrape_run)
    db.commit()

    return ManualFetchResult(
        profiles_checked=len(active_profiles),
        items_returned=len(items),
        parsed_count=pipeline_result.parsed_count,
        inserted_count=pipeline_result.inserted_count,
        skipped_count=pipeline_result.skipped_count,
        provider_run_id=run_id,
        provider_dataset_id=str(dataset_id),
        status=status,
        usage_total_usd=run_details.get("usageTotalUsd"),
        charged_event_counts=run_details.get("chargedEventCounts"),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _safe_run_metadata(run: dict[str, Any], run_details: dict[str, Any]) -> dict[str, Any]:
    return {
        "run": {
            "id": run.get("id"),
            "status": run.get("status"),
            "defaultDatasetId": run.get("defaultDatasetId"),
            "startedAt": run.get("startedAt"),
            "finishedAt": run.get("finishedAt"),
        },
        "cost": {
            "usageTotalUsd": run_details.get("usageTotalUsd"),
            "chargedEventCounts": run_details.get("chargedEventCounts"),
        },
    }
