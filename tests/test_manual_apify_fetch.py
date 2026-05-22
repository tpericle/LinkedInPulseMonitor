from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db import Base
from app.manual_fetch import GuardedFetchError, run_manual_apify_fetch
from app.models import Person, Post, ScrapeRun
from app.people import add_tracked_profile


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


class FakeApifyClient:
    def __init__(self, items: list[dict] | None = None) -> None:
        self.items = items or []
        self.actor_input: dict | None = None
        self.max_total_charge_usd: float | None = None
        self.run_called = False

    def run_actor(
        self,
        actor_id: str,
        actor_input: dict,
        max_total_charge_usd: float,
    ) -> dict:
        self.run_called = True
        self.actor_input = actor_input
        self.max_total_charge_usd = max_total_charge_usd
        return {
            "id": "run-123",
            "status": "SUCCEEDED",
            "defaultDatasetId": "dataset-123",
            "startedAt": "2026-05-21T12:00:00.000Z",
            "finishedAt": "2026-05-21T12:00:06.000Z",
        }

    def fetch_dataset_items(self, dataset_id: str) -> list[dict]:
        assert dataset_id == "dataset-123"
        return self.items

    def fetch_run_details(self, run_id: str) -> dict:
        assert run_id == "run-123"
        return {
            "id": "run-123",
            "status": "SUCCEEDED",
            "usageTotalUsd": 0.011,
            "chargedEventCounts": {"actor-start-gb": 1, "post": 1},
        }


def test_manual_fetch_uses_active_profiles_and_ingests_recent_posts(db_session: Session):
    now = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
    add_tracked_profile(
        db_session,
        linkedin_url="https://www.linkedin.com/in/dharmesh/",
        full_name="Dharmesh Shah",
    )
    inactive = add_tracked_profile(
        db_session,
        linkedin_url="https://www.linkedin.com/in/danielpink/",
        full_name="Daniel Pink",
    )
    inactive.is_active = False
    db_session.commit()
    client = FakeApifyClient(
        items=[
            {
                "id": "post-1",
                "postedAtISO": "2026-05-21T10:00:00.000Z",
                "text": "A recent LinkedIn post.",
                "url": "https://www.linkedin.com/feed/update/urn:li:activity:1/",
                "authorName": "Dharmesh Shah",
                "authorProfileUrl": "https://www.linkedin.com/in/dharmesh/",
                "type": "post",
            }
        ]
    )

    result = run_manual_apify_fetch(
        db_session,
        client=client,
        actor_id="supreme_coder/linkedin-post",
        now=now,
    )

    stored_post = db_session.scalars(select(Post)).one()
    stored_run = db_session.scalars(select(ScrapeRun)).one()
    assert client.actor_input == {
        "deepScrape": True,
        "limitPerSource": 3,
        "rawData": False,
        "urls": ["https://www.linkedin.com/in/dharmesh/"],
    }
    assert client.max_total_charge_usd == 1.0
    assert stored_post.author_name == "Dharmesh Shah"
    assert stored_run.provider == "apify"
    assert stored_run.provider_run_id == "run-123"
    assert stored_run.provider_dataset_id == "dataset-123"
    assert stored_run.status == "SUCCEEDED"
    assert stored_run.item_count == 1
    assert result.profiles_checked == 1
    assert result.items_returned == 1
    assert result.inserted_count == 1
    assert result.skipped_count == 0
    assert result.usage_total_usd == 0.011
    assert result.charged_event_counts == {"actor-start-gb": 1, "post": 1}


def test_manual_fetch_accepts_custom_lookback_for_one_off_backfill(db_session: Session):
    now = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
    add_tracked_profile(
        db_session,
        linkedin_url="https://www.linkedin.com/in/dharmesh/",
        full_name="Dharmesh Shah",
    )
    client = FakeApifyClient(
        items=[
            {
                "id": "post-72h",
                "postedAtISO": "2026-05-19T12:30:00.000Z",
                "text": "A post from within the 72 hour backfill window.",
                "url": "https://www.linkedin.com/feed/update/urn:li:activity:72/",
                "authorName": "Dharmesh Shah",
                "authorProfileUrl": "https://www.linkedin.com/in/dharmesh/",
                "type": "post",
            }
        ]
    )

    result = run_manual_apify_fetch(
        db_session,
        client=client,
        actor_id="supreme_coder/linkedin-post",
        now=now,
        lookback=timedelta(hours=72),
    )

    stored_post = db_session.scalars(select(Post)).one()
    assert stored_post.source_post_id == "post-72h"
    assert result.parsed_count == 1
    assert result.inserted_count == 1


def test_manual_fetch_refuses_more_than_max_active_profiles(db_session: Session):
    for index in range(4):
        db_session.add(
            Person(
                full_name=f"Person {index}",
                linkedin_url=f"https://www.linkedin.com/in/person-{index}/",
                is_active=True,
            )
        )
    db_session.commit()
    client = FakeApifyClient()

    with pytest.raises(GuardedFetchError, match="4 active profiles"):
        run_manual_apify_fetch(db_session, client=client, actor_id="actor-id", max_profiles=3)

    assert client.run_called is False


def test_manual_fetch_refuses_when_no_active_profiles(db_session: Session):
    add_tracked_profile(
        db_session,
        linkedin_url="https://www.linkedin.com/in/dharmesh/",
        full_name="Dharmesh Shah",
    )
    db_session.scalars(select(Person)).one().is_active = False
    db_session.commit()
    client = FakeApifyClient()

    with pytest.raises(GuardedFetchError, match="no active profiles"):
        run_manual_apify_fetch(db_session, client=client, actor_id="actor-id")

    assert client.run_called is False
