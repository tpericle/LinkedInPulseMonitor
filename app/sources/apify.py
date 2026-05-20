from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.sources.base import PostInput

DEFAULT_LOOKBACK = timedelta(hours=24)
SOURCE_NAME = "apify"


def parse_apify_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_apify_posts(
    items: Iterable[dict[str, Any]],
    *,
    now: datetime | None = None,
    lookback: timedelta = DEFAULT_LOOKBACK,
) -> list[PostInput]:
    now = now or datetime.now(UTC)
    cutoff = now - lookback
    posts: list[PostInput] = []

    for item in items:
        posted_at_value = item.get("postedAtISO")
        if not posted_at_value:
            continue

        try:
            authored_at = parse_apify_timestamp(posted_at_value)
        except ValueError:
            continue
        if authored_at < cutoff:
            continue

        content = item.get("text", "").strip()
        if not content:
            continue

        posts.append(
            PostInput(
                source=SOURCE_NAME,
                source_post_id=item.get("shareUrn") or item.get("urn") or item.get("id"),
                linkedin_url=item.get("url"),
                author_name=item.get("authorName"),
                author_profile_url=item.get("authorProfileUrl"),
                content=content,
                post_type=item.get("type") or "post",
                authored_at=authored_at,
                raw=item,
            )
        )

    return posts
