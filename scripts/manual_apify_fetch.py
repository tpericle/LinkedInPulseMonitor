from __future__ import annotations

import argparse

from app.apify_http import ApifyHttpClient
from app.config import get_settings
from app.db import SessionLocal, create_db
from app.manual_fetch import (
    DEFAULT_LIMIT_PER_SOURCE,
    DEFAULT_MAX_PROFILES,
    DEFAULT_MAX_TOTAL_CHARGE_USD,
    ManualFetchResult,
    run_manual_apify_fetch,
)


def format_fetch_result(result: ManualFetchResult) -> str:
    return "\n".join(
        [
            "Manual Apify fetch complete.",
            f"status: {result.status}",
            f"profiles checked: {result.profiles_checked}",
            f"items returned: {result.items_returned}",
            f"parsed recent posts: {result.parsed_count}",
            f"new posts inserted: {result.inserted_count}",
            f"skipped items/posts: {result.skipped_count}",
            f"run id: {result.provider_run_id}",
            f"dataset id: {result.provider_dataset_id}",
            f"usage total USD: {result.usage_total_usd}",
            f"charged events: {result.charged_event_counts}",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a guarded manual Apify fetch.")
    parser.add_argument("--max-profiles", type=int, default=DEFAULT_MAX_PROFILES)
    parser.add_argument("--limit-per-source", type=int, default=DEFAULT_LIMIT_PER_SOURCE)
    parser.add_argument("--max-total-charge-usd", type=float, default=DEFAULT_MAX_TOTAL_CHARGE_USD)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    if not settings.apify_token or not settings.apify_actor_id:
        raise SystemExit("Missing APIFY_TOKEN or APIFY_ACTOR_ID in environment/.env.")

    create_db()
    with SessionLocal() as db, ApifyHttpClient(token=settings.apify_token) as client:
        result = run_manual_apify_fetch(
            db,
            client=client,
            actor_id=settings.apify_actor_id,
            max_profiles=args.max_profiles,
            limit_per_source=args.limit_per_source,
            max_total_charge_usd=args.max_total_charge_usd,
        )
    print(format_fetch_result(result))


if __name__ == "__main__":
    main()
