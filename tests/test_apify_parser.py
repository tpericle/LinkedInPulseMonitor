from datetime import UTC, datetime, timedelta

from app.sources.apify import parse_apify_posts
from app.sources.base import PostInput


def test_parse_apify_posts_normalizes_recent_item():
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    item = {
        "type": "document",
        "urn": "urn:li:activity:7462883894476918784",
        "shareUrn": "urn:li:ugcPost:7462883858670276608",
        "url": "https://www.linkedin.com/posts/arthur-c-brooks_example",
        "text": "Loving someone is a doing word.",
        "authorName": "Dr. Arthur Brooks",
        "authorProfileUrl": "https://www.linkedin.com/in/arthur-c-brooks",
        "postedAtISO": "2026-05-20T15:16:14.121Z",
        "inputUrl": "https://www.linkedin.com/in/arthur-c-brooks/",
    }

    posts = parse_apify_posts([item], now=now)

    assert posts == [
        PostInput(
            source="apify",
            source_post_id="urn:li:ugcPost:7462883858670276608",
            linkedin_url="https://www.linkedin.com/posts/arthur-c-brooks_example",
            author_name="Dr. Arthur Brooks",
            author_profile_url="https://www.linkedin.com/in/arthur-c-brooks",
            content="Loving someone is a doing word.",
            post_type="document",
            authored_at=datetime(2026, 5, 20, 15, 16, 14, 121000, tzinfo=UTC),
            raw=item,
        )
    ]


def test_parse_apify_posts_keeps_only_last_24_hours_by_default():
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    items = [
        {"id": "recent", "text": "Recent", "postedAtISO": "2026-05-20T19:00:00.000Z"},
        {"id": "boundary", "text": "Boundary", "postedAtISO": "2026-05-19T20:00:00.000Z"},
        {"id": "old", "text": "Old", "postedAtISO": "2026-05-19T19:59:59.999Z"},
        {"id": "missing_timestamp", "text": "No timestamp"},
    ]

    posts = parse_apify_posts(items, now=now)

    assert [post.content for post in posts] == ["Recent", "Boundary"]


def test_parse_apify_posts_allows_explicit_backfill_window():
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    items = [
        {"id": "within_48h", "text": "Within 48h", "postedAtISO": "2026-05-19T00:00:00.000Z"},
        {"id": "outside_48h", "text": "Outside 48h", "postedAtISO": "2026-05-18T19:59:59.999Z"},
    ]

    posts = parse_apify_posts(items, now=now, lookback=timedelta(hours=48))

    assert [post.content for post in posts] == ["Within 48h"]


def test_parse_apify_posts_skips_items_without_text():
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    items = [
        {"id": "blank", "text": "   ", "postedAtISO": "2026-05-20T19:00:00.000Z"},
        {"id": "missing", "postedAtISO": "2026-05-20T19:00:00.000Z"},
    ]

    posts = parse_apify_posts(items, now=now)

    assert posts == []


def test_parse_apify_posts_skips_items_with_invalid_timestamp():
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    items = [
        {"id": "bad", "text": "Bad timestamp", "postedAtISO": "not-a-date"},
        {"id": "good", "text": "Good timestamp", "postedAtISO": "2026-05-20T19:00:00.000Z"},
    ]

    posts = parse_apify_posts(items, now=now)

    assert [post.content for post in posts] == ["Good timestamp"]
