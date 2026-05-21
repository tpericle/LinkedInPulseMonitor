from datetime import UTC, datetime, timedelta

from scripts.apify_spike import (
    SPIKE_PROFILES,
    build_actor_input,
    filter_recent_items,
    summarize_run_cost,
)


def test_build_actor_input_uses_actor_controls_for_limited_recent_scrape():
    actor_input = build_actor_input("urls")

    assert actor_input == {
        "deepScrape": True,
        "limitPerSource": 3,
        "rawData": False,
        "urls": SPIKE_PROFILES,
    }


def test_build_actor_input_allows_explicit_limit_per_source():
    actor_input = build_actor_input("urls", limit_per_source=5)

    assert actor_input["limitPerSource"] == 5


def test_summarize_run_cost_exposes_charge_fields_when_available():
    summary = summarize_run_cost(
        {
            "id": "run-123",
            "status": "SUCCEEDED",
            "usageTotalUsd": 0.006,
            "chargedEventCounts": {"actor-start-gb": 1, "post": 4},
        }
    )

    assert summary == {
        "id": "run-123",
        "status": "SUCCEEDED",
        "usageTotalUsd": 0.006,
        "chargedEventCounts": {"actor-start-gb": 1, "post": 4},
    }


def test_filter_recent_items_keeps_only_items_from_last_24_hours():
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    items = [
        {"id": "recent", "postedAtISO": "2026-05-20T15:16:14.121Z"},
        {"id": "boundary", "postedAtISO": "2026-05-19T20:00:00.000Z"},
        {"id": "old", "postedAtISO": "2026-05-19T19:59:59.999Z"},
        {"id": "missing"},
    ]

    filtered = filter_recent_items(items, now=now, lookback=timedelta(hours=24))

    assert [item["id"] for item in filtered] == ["recent", "boundary"]
