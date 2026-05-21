from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db import Base
from app.models import Person
from app.people import add_tracked_profile


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


def test_add_tracked_profile_stores_linkedin_profile(db_session: Session):
    person = add_tracked_profile(
        db_session,
        linkedin_url="https://www.linkedin.com/in/arthur-c-brooks/",
        full_name="Dr. Arthur Brooks",
        company="Harvard",
        tags=["leadership", "wellbeing"],
    )

    stored_person = db_session.scalars(select(Person)).one()
    assert person.id == stored_person.id
    assert stored_person.linkedin_url == "https://www.linkedin.com/in/arthur-c-brooks/"
    assert stored_person.full_name == "Dr. Arthur Brooks"
    assert stored_person.company == "Harvard"
    assert stored_person.tags_json == '["leadership", "wellbeing"]'
    assert stored_person.is_active is True


def test_add_tracked_profile_is_idempotent_for_trailing_slash_variants(db_session: Session):
    first = add_tracked_profile(db_session, linkedin_url="https://www.linkedin.com/in/danielpink")
    second = add_tracked_profile(db_session, linkedin_url="https://www.linkedin.com/in/danielpink/")

    stored_people = db_session.scalars(select(Person)).all()
    assert first.id == second.id
    assert len(stored_people) == 1
    assert stored_people[0].linkedin_url == "https://www.linkedin.com/in/danielpink/"
