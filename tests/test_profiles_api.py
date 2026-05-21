from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db import Base, get_db
from app.main import app
from app.models import Person


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


def test_create_profile_endpoint_tracks_linkedin_profile(
    db_session: Session, client_with_db: TestClient
):
    response = client_with_db.post(
        "/profiles",
        json={
            "linkedin_url": "https://www.linkedin.com/in/dharmesh",
            "full_name": "Dharmesh Shah",
            "company": "HubSpot",
            "tags": ["startup", "marketing"],
        },
    )

    stored_person = db_session.scalars(select(Person)).one()
    assert response.status_code == 201
    assert response.json() == {
        "id": stored_person.id,
        "linkedin_url": "https://www.linkedin.com/in/dharmesh/",
        "full_name": "Dharmesh Shah",
        "company": "HubSpot",
        "tags": ["startup", "marketing"],
        "is_active": True,
    }
