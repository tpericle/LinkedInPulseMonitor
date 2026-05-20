import json
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db import Base
from app.ingest import ingest_posts
from app.models import Person, Post
from app.sources.base import PostInput


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


def make_post_input(
    *,
    source_post_id: str | None = "urn:li:ugcPost:1",
    author_profile_url: str | None = "https://www.linkedin.com/in/arthur-c-brooks",
) -> PostInput:
    return PostInput(
        source="apify",
        source_post_id=source_post_id,
        linkedin_url="https://www.linkedin.com/posts/arthur-c-brooks_example",
        author_name="Dr. Arthur Brooks",
        author_profile_url=author_profile_url,
        content="Loving someone is a doing word.",
        post_type="document",
        authored_at=datetime(2026, 5, 20, 15, 16, 14, 121000, tzinfo=UTC),
        raw={"shareUrn": source_post_id, "text": "Loving someone is a doing word."},
    )


def test_ingest_posts_inserts_parsed_post(db_session: Session):
    result = ingest_posts(db_session, [make_post_input()])

    stored_post = db_session.scalars(select(Post)).one()
    assert result.inserted_count == 1
    assert result.skipped_count == 0
    assert stored_post.source == "apify"
    assert stored_post.source_post_id == "urn:li:ugcPost:1"
    assert stored_post.linkedin_url == "https://www.linkedin.com/posts/arthur-c-brooks_example"
    assert stored_post.author_name == "Dr. Arthur Brooks"
    assert stored_post.author_profile_url == "https://www.linkedin.com/in/arthur-c-brooks"
    assert stored_post.content == "Loving someone is a doing word."
    assert stored_post.post_type == "document"
    assert stored_post.authored_at == datetime(2026, 5, 20, 15, 16, 14, 121000)
    assert json.loads(stored_post.raw_json) == {
        "shareUrn": "urn:li:ugcPost:1",
        "text": "Loving someone is a doing word.",
    }


def test_ingest_posts_skips_duplicate_source_post_id(db_session: Session):
    first = make_post_input(source_post_id="urn:li:ugcPost:duplicate")
    duplicate = make_post_input(source_post_id="urn:li:ugcPost:duplicate")

    first_result = ingest_posts(db_session, [first])
    second_result = ingest_posts(db_session, [duplicate])

    assert first_result.inserted_count == 1
    assert second_result.inserted_count == 0
    assert second_result.skipped_count == 1
    assert len(db_session.scalars(select(Post)).all()) == 1


def test_ingest_posts_links_matching_person_by_author_profile_url(db_session: Session):
    person = Person(
        full_name="Dr. Arthur Brooks",
        linkedin_url="https://www.linkedin.com/in/arthur-c-brooks/",
    )
    db_session.add(person)
    db_session.commit()

    result = ingest_posts(db_session, [make_post_input()])

    stored_post = db_session.scalars(select(Post)).one()
    assert result.inserted_count == 1
    assert stored_post.person_id == person.id


def test_ingest_posts_matches_person_when_url_slash_format_differs(db_session: Session):
    person = Person(
        full_name="Dr. Arthur Brooks",
        linkedin_url="https://www.linkedin.com/in/arthur-c-brooks",
    )
    db_session.add(person)
    db_session.commit()

    result = ingest_posts(
        db_session,
        [make_post_input(author_profile_url="https://www.linkedin.com/in/arthur-c-brooks/")],
    )

    stored_post = db_session.scalars(select(Post)).one()
    assert result.inserted_count == 1
    assert stored_post.person_id == person.id


def test_ingest_posts_skips_posts_without_source_post_id(db_session: Session):
    result = ingest_posts(db_session, [make_post_input(source_post_id=None)])

    assert result.inserted_count == 0
    assert result.skipped_count == 1
    assert db_session.scalars(select(Post)).all() == []
