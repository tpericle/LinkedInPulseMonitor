"""Small Apify actor spike helper.

This is intentionally a lightweight, inspectable script rather than production app code.
It can:

1. Confirm local Apify config is present.
2. Inspect the selected actor metadata without printing secrets.
3. Optionally run the actor against Tony's three spike profiles and save dataset output.

Usage:
    python scripts/apify_spike.py --inspect
    python scripts/apify_spike.py --run --input-key urls

If the actor expects a different input shape, pass --input-key with the field shown in
Apify Console's actor input UI.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

SPIKE_PROFILES = [
    "https://www.linkedin.com/in/arthur-c-brooks/",
    "https://www.linkedin.com/in/danielpink/",
    "https://www.linkedin.com/in/dharmesh/",
]

DEFAULT_FIXTURE_PATH = Path("tests/fixtures/apify_sample_posts.json")
APIFY_API_BASE = "https://api.apify.com/v2"


def require_config() -> tuple[str, str]:
    load_dotenv(".env")
    token = os.environ.get("APIFY_TOKEN")
    actor_id = os.environ.get("APIFY_ACTOR_ID")

    config_values = {"APIFY_TOKEN": token, "APIFY_ACTOR_ID": actor_id}
    missing = [name for name, value in config_values.items() if not value]
    if missing:
        names = ", ".join(missing)
        raise SystemExit(f"Missing required .env value(s): {names}")

    return token or "", actor_id or ""


def apify_client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=APIFY_API_BASE,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )


def inspect_actor(client: httpx.Client, actor_id: str) -> dict[str, Any]:
    response = client.get(f"/acts/{actor_id}")
    response.raise_for_status()
    data = response.json()["data"]
    return {
        "id": data.get("id"),
        "username": data.get("username"),
        "name": data.get("name"),
        "title": data.get("title"),
        "pricing": [info.get("pricingModel") for info in data.get("pricingInfos", [])],
        "default_run_options": data.get("defaultRunOptions"),
    }


def build_actor_input(input_key: str, *, limit_per_source: int = 3) -> dict[str, Any]:
    return {
        "deepScrape": True,
        "limitPerSource": limit_per_source,
        "rawData": False,
        input_key: SPIKE_PROFILES,
    }


def summarize_run_cost(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run.get("id"),
        "status": run.get("status"),
        "usageTotalUsd": run.get("usageTotalUsd"),
        "chargedEventCounts": run.get("chargedEventCounts"),
    }


def run_actor(
    client: httpx.Client,
    actor_id: str,
    actor_input: dict[str, Any],
    max_total_charge_usd: float,
) -> dict[str, Any]:
    response = client.post(
        f"/acts/{actor_id}/runs",
        params={
            "waitForFinish": 180,
            "maxTotalChargeUsd": max_total_charge_usd,
        },
        json=actor_input,
    )
    response.raise_for_status()
    return response.json()["data"]


def fetch_dataset_items(client: httpx.Client, dataset_id: str) -> list[dict[str, Any]]:
    response = client.get(
        f"/datasets/{dataset_id}/items",
        params={"clean": "true", "format": "json"},
    )
    response.raise_for_status()
    return response.json()


def fetch_run_details(client: httpx.Client, run_id: str) -> dict[str, Any]:
    response = client.get(f"/actor-runs/{run_id}")
    response.raise_for_status()
    return response.json()["data"]


def parse_apify_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def filter_recent_items(
    items: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    lookback: timedelta = timedelta(hours=24),
) -> list[dict[str, Any]]:
    cutoff = (now or datetime.now(UTC)) - lookback
    recent_items = []

    for item in items:
        posted_at = item.get("postedAtISO")
        if not posted_at:
            continue
        if parse_apify_timestamp(posted_at) >= cutoff:
            recent_items.append(item)

    return recent_items


def save_fixture(items: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect or run the selected Apify LinkedIn actor."
    )
    parser.add_argument("--inspect", action="store_true", help="Inspect actor metadata only.")
    parser.add_argument("--run", action="store_true", help="Run actor and save dataset items.")
    parser.add_argument(
        "--input-key",
        default="urls",
        help="Input field containing the LinkedIn profile URLs. Default: urls.",
    )
    parser.add_argument(
        "--limit-per-source",
        type=int,
        default=3,
        help="Maximum latest posts to request per profile. Default: 3.",
    )
    parser.add_argument(
        "--max-total-charge-usd",
        type=float,
        default=1.0,
        help="Safety cap for this spike run. Default: 1.0.",
    )
    parser.add_argument(
        "--fixture-path",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help=f"Where to save dataset JSON. Default: {DEFAULT_FIXTURE_PATH}",
    )
    args = parser.parse_args()

    if not args.inspect and not args.run:
        parser.error("Choose --inspect or --run")

    token, actor_id = require_config()

    with apify_client(token) as client:
        actor_summary = inspect_actor(client, actor_id)
        print("Actor:")
        print(json.dumps(actor_summary, indent=2))
        print("\nSpike profiles:")
        print(json.dumps(SPIKE_PROFILES, indent=2))
        print("\nCandidate actor input:")
        print(
            json.dumps(
                build_actor_input(args.input_key, limit_per_source=args.limit_per_source),
                indent=2,
            )
        )

        if args.inspect:
            return

        actor_input = build_actor_input(args.input_key, limit_per_source=args.limit_per_source)
        run = run_actor(client, actor_id, actor_input, args.max_total_charge_usd)
        dataset_id = run.get("defaultDatasetId")
        print("\nRun result:")
        print(
            json.dumps(
                {
                    "id": run.get("id"),
                    "status": run.get("status"),
                    "defaultDatasetId": dataset_id,
                    "startedAt": run.get("startedAt"),
                    "finishedAt": run.get("finishedAt"),
                    "usageTotalUsd": run.get("usageTotalUsd"),
                    "chargedEventCounts": run.get("chargedEventCounts"),
                },
                indent=2,
            )
        )

        if not dataset_id:
            raise SystemExit("Actor run did not return a defaultDatasetId.")

        items = filter_recent_items(fetch_dataset_items(client, dataset_id))
        save_fixture(items, args.fixture_path)
        run_details = fetch_run_details(client, str(run.get("id")))
        print("\nCost summary:")
        print(json.dumps(summarize_run_cost(run_details), indent=2))
        print(f"\nSaved {len(items)} recent dataset item(s) to {args.fixture_path}")


if __name__ == "__main__":
    main()
