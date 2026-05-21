from collections.abc import Generator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db import Base, get_db
from app.main import app
from app.models import DailyReport, Post


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


def test_generate_daily_report_endpoint_creates_report(
    db_session: Session, client_with_db: TestClient
):
    db_session.add(
        Post(
            source="apify",
            source_post_id="post-1",
            author_name="Recent Author",
            content="Report endpoint should summarize this post.",
            post_type="post",
            authored_at=datetime(2026, 5, 20, 18, 0),
            raw_json="{}",
        )
    )
    db_session.commit()

    response = client_with_db.post("/reports/daily", json={"now": "2026-05-20T20:00:00Z"})

    stored_report = db_session.scalars(select(DailyReport)).one()
    assert response.status_code == 201
    assert response.json() == {
        "id": stored_report.id,
        "report_date": "2026-05-20",
        "post_count": 1,
        "summary_text": "Mock summary for 1 recent LinkedIn post.",
    }
