import json
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db import Base
from app.models import DailyReport, Post
from app.reports import generate_daily_report


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


def test_generate_daily_report_summarizes_posts_from_last_24_hours(db_session: Session):
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    recent_post = Post(
        source="apify",
        source_post_id="recent",
        author_name="Recent Author",
        content="AI agents are changing how teams learn from customers.",
        post_type="post",
        authored_at=now.replace(tzinfo=None) - timedelta(hours=2),
        raw_json="{}",
    )
    old_post = Post(
        source="apify",
        source_post_id="old",
        author_name="Old Author",
        content="This older post should not affect today's report.",
        post_type="post",
        authored_at=now.replace(tzinfo=None) - timedelta(days=2),
        raw_json="{}",
    )
    db_session.add_all([recent_post, old_post])
    db_session.commit()

    result = generate_daily_report(db_session, now=now)

    stored_report = db_session.scalars(select(DailyReport)).one()
    assert result.report_id == stored_report.id
    assert stored_report.report_date == date(2026, 5, 20)
    assert stored_report.post_count == 1
    assert stored_report.summary_text == "Mock summary for 1 recent LinkedIn post."
    assert json.loads(stored_report.themes_json) == [
        {"theme": "AI", "confidence": 1.0, "post_count": 1}
    ]
    assert json.loads(stored_report.notable_posts_json) == [
        {
            "author_name": "Recent Author",
            "content": "AI agents are changing how teams learn from customers.",
            "linkedin_url": None,
            "possible_event": False,
        }
    ]


def test_generate_daily_report_replaces_existing_report_for_same_date(db_session: Session):
    now = datetime(2026, 5, 20, 20, 0, tzinfo=UTC)
    db_session.add(
        DailyReport(
            report_date=date(2026, 5, 20),
            post_count=0,
            summary_text="Old mock report.",
            themes_json="[]",
            notable_posts_json="[]",
        )
    )
    db_session.add(
        Post(
            source="apify",
            source_post_id="recent",
            author_name="Recent Author",
            content="New report should replace the stale one.",
            post_type="post",
            authored_at=now.replace(tzinfo=None) - timedelta(hours=1),
            raw_json="{}",
        )
    )
    db_session.commit()

    generate_daily_report(db_session, now=now)

    reports = db_session.scalars(select(DailyReport)).all()
    assert len(reports) == 1
    assert reports[0].post_count == 1
    assert reports[0].summary_text == "Mock summary for 1 recent LinkedIn post."
