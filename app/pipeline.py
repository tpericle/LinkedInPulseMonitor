from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.ingest import ingest_posts
from app.sources.apify import DEFAULT_LOOKBACK, parse_apify_posts


@dataclass(frozen=True)
class PipelineResult:
    parsed_count: int
    inserted_count: int
    skipped_count: int


def ingest_apify_items(
    db: Session,
    items: Iterable[dict[str, Any]],
    *,
    now: datetime | None = None,
    lookback: timedelta = DEFAULT_LOOKBACK,
) -> PipelineResult:
    item_list = list(items)
    posts = parse_apify_posts(item_list, now=now, lookback=lookback)
    ingest_result = ingest_posts(db, posts)
    parse_skipped_count = len(item_list) - len(posts)
    return PipelineResult(
        parsed_count=len(posts),
        inserted_count=ingest_result.inserted_count,
        skipped_count=parse_skipped_count + ingest_result.skipped_count,
    )
