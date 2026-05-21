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
from app.models import Post


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


def test_ingest_apify_items_endpoint_stores_recent_posts(
    db_session: Session, client_with_db: TestClient
):
    response = client_with_db.post(
        "/ingest/apify-items",
        json={
            "now": "2026-05-20T20:00:00Z",
            "items": [
                {
                    "shareUrn": "urn:li:ugcPost:api-recent",
                    "text": "API ingestion should store this post.",
                    "postedAtISO": "2026-05-20T19:00:00.000Z",
                },
                {
                    "shareUrn": "urn:li:ugcPost:api-old",
                    "text": "API ingestion should skip this older post.",
                    "postedAtISO": "2026-05-19T19:59:59.999Z",
                },
            ],
        },
    )

    stored_posts = db_session.scalars(select(Post)).all()
    assert response.status_code == 201
    assert response.json() == {"parsed_count": 1, "inserted_count": 1, "skipped_count": 1}
    assert [post.source_post_id for post in stored_posts] == ["urn:li:ugcPost:api-recent"]
    assert stored_posts[0].authored_at == datetime(2026, 5, 20, 19, 0)
