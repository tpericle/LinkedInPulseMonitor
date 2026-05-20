from datetime import UTC, datetime, timedelta

from scripts.apify_spike import SPIKE_PROFILES, build_actor_input, filter_recent_items


def test_build_actor_input_uses_actor_controls_for_limited_recent_scrape():
    actor_input = build_actor_input("urls")

    assert actor_input == {
        "deepScrape": True,
        "limitPerSource": 10,
        "rawData": False,
        "urls": SPIKE_PROFILES,
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
