from collections.abc import Generator
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db import Base, get_db
from app.main import app
from app.models import DailyReport, Person, Post


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


@pytest.fixture
def client_with_db(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_reports_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_renders_project_name():
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "LinkedIn Pulse Monitor" in response.text


def test_dashboard_renders_guided_profile_form():
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Add a profile to follow" in response.text
    assert "LinkedIn profile URL" in response.text
    assert "https://www.linkedin.com/in/" in response.text
    assert "name=\"linkedin_url\"" in response.text
    assert "name=\"full_name\"" in response.text
    assert "name=\"company\"" in response.text
    assert "name=\"tags\"" in response.text
    assert "Start following" in response.text


def test_dashboard_renders_recent_posts_and_latest_report(
    db_session: Session, client_with_db: TestClient
):
    db_session.add(
        Post(
            source="apify",
            source_post_id="post-1",
            author_name="Recent Author",
            content="Dashboard should show this post.",
            post_type="post",
            authored_at=datetime(2026, 5, 20, 18, 0),
            raw_json="{}",
        )
    )
    db_session.add(
        DailyReport(
            report_date=date(2026, 5, 20),
            post_count=1,
            summary_text="Dashboard should show this report.",
            themes_json="[]",
            notable_posts_json="[]",
        )
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert "Recent Author" in response.text
    assert "Dashboard should show this post." in response.text
    assert "Dashboard should show this report." in response.text


def test_dashboard_renders_tracked_profiles(db_session: Session, client_with_db: TestClient):
    db_session.add(
        Person(
            full_name="Dr. Arthur Brooks",
            company="Harvard",
            linkedin_url="https://www.linkedin.com/in/arthur-c-brooks/",
        )
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert "Dr. Arthur Brooks" in response.text
    assert "Harvard" in response.text
