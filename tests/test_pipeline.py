from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db import Base
from app.models import Post
from app.pipeline import ingest_apify_items


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


def test_ingest_apify_items_parses_recent_items_and_stores_them(db_session: Session):
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    items = [
        {
            "shareUrn": "urn:li:ugcPost:recent",
            "url": "https://www.linkedin.com/posts/example_recent",
            "text": "Recent post worth digesting.",
            "authorName": "Recent Author",
            "authorProfileUrl": "https://www.linkedin.com/in/recent-author",
            "postedAtISO": "2026-05-20T19:00:00.000Z",
        },
        {
            "shareUrn": "urn:li:ugcPost:old",
            "text": "Old post should not be stored.",
            "postedAtISO": "2026-05-19T19:59:59.999Z",
        },
    ]

    result = ingest_apify_items(db_session, items, now=now)

    stored_posts = db_session.scalars(select(Post)).all()
    assert result.parsed_count == 1
    assert result.inserted_count == 1
    assert result.skipped_count == 1
    assert [post.source_post_id for post in stored_posts] == ["urn:li:ugcPost:recent"]
    assert stored_posts[0].content == "Recent post worth digesting."


def test_ingest_apify_items_reports_duplicate_posts_as_skipped(db_session: Session):
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    item = {
        "shareUrn": "urn:li:ugcPost:duplicate",
        "text": "Same post appears twice.",
        "postedAtISO": "2026-05-20T19:00:00.000Z",
    }

    first_result = ingest_apify_items(db_session, [item], now=now)
    second_result = ingest_apify_items(db_session, [item], now=now)

    stored_posts = db_session.scalars(select(Post)).all()
    assert first_result.parsed_count == 1
    assert first_result.inserted_count == 1
    assert first_result.skipped_count == 0
    assert second_result.parsed_count == 1
    assert second_result.inserted_count == 0
    assert second_result.skipped_count == 1
    assert len(stored_posts) == 1
