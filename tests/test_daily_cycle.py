from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.daily_cycle import DailyCycleResult, format_daily_cycle_recap, run_daily_cycle
from app.db import Base
from app.manual_fetch import ManualFetchResult
from app.models import DailyReport


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


def test_daily_cycle_runs_fetch_then_generates_report(monkeypatch, db_session: Session):
    calls = []

    def fake_fetch(db: Session) -> ManualFetchResult:
        calls.append(("fetch", db))
        return ManualFetchResult(
            profiles_checked=2,
            items_returned=5,
            parsed_count=4,
            inserted_count=3,
            skipped_count=1,
            provider_run_id="run-123",
            provider_dataset_id="dataset-123",
            status="SUCCEEDED",
            usage_total_usd=0.025,
            charged_event_counts={"post": 5},
        )

    def fake_generate_report(db: Session, *, now: datetime | None = None):
        calls.append(("report", db, now))
        report = DailyReport(
            report_date=now.date(),
            post_count=3,
            summary_text="Mock summary for 3 recent LinkedIn posts.",
            themes_json="[]",
            notable_posts_json="[]",
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        class Result:
            report_id = report.id

        return Result()

    monkeypatch.setattr("app.daily_cycle.run_dashboard_apify_fetch", fake_fetch)
    monkeypatch.setattr("app.daily_cycle.generate_daily_report", fake_generate_report)

    now = datetime(2026, 5, 24, 14, 30, tzinfo=UTC)
    result = run_daily_cycle(db_session, now=now)

    assert calls == [("fetch", db_session), ("report", db_session, now)]
    assert result == DailyCycleResult(
        fetch_result=ManualFetchResult(
            profiles_checked=2,
            items_returned=5,
            parsed_count=4,
            inserted_count=3,
            skipped_count=1,
            provider_run_id="run-123",
            provider_dataset_id="dataset-123",
            status="SUCCEEDED",
            usage_total_usd=0.025,
            charged_event_counts={"post": 5},
        ),
        report_id=1,
    )


def test_daily_cycle_recap_is_concise_and_names_cost():
    result = DailyCycleResult(
        fetch_result=ManualFetchResult(
            profiles_checked=1,
            items_returned=2,
            parsed_count=2,
            inserted_count=0,
            skipped_count=2,
            provider_run_id="run-123",
            provider_dataset_id="dataset-123",
            status="SUCCEEDED",
            usage_total_usd=None,
            charged_event_counts=None,
        ),
        report_id=7,
    )

    recap = format_daily_cycle_recap(result)

    assert "Daily cycle complete" in recap
    assert "What ran:" in recap
    assert "profiles checked: 1" in recap
    assert "items returned: 2" in recap
    assert "parsed: 2" in recap
    assert "inserted: 0" in recap
    assert "skipped: 2" in recap
    assert "provider status: SUCCEEDED" in recap
    assert "estimated Apify cost: unavailable" in recap
    assert "report id: 7" in recap
    assert "Notification recommendation: stay quiet; no new posts were saved." in recap


def test_daily_cycle_recap_recommends_notification_when_new_posts_exist():
    result = DailyCycleResult(
        fetch_result=ManualFetchResult(
            profiles_checked=3,
            items_returned=6,
            parsed_count=5,
            inserted_count=2,
            skipped_count=3,
            provider_run_id="run-456",
            provider_dataset_id="dataset-456",
            status="SUCCEEDED",
            usage_total_usd=0.031,
            charged_event_counts={"post": 6},
        ),
        report_id=8,
    )

    recap = format_daily_cycle_recap(result)

    assert "inserted: 2" in recap
    assert "estimated Apify cost: $0.031" in recap
    assert "Notification recommendation: notify Tony; 2 new posts were saved." in recap
