import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Person, Post
from app.sources.base import PostInput


@dataclass(frozen=True)
class IngestResult:
    inserted_count: int
    skipped_count: int


def ingest_posts(db: Session, posts: list[PostInput]) -> IngestResult:
    inserted_count = 0
    skipped_count = 0

    for post_input in posts:
        if not post_input.source_post_id:
            skipped_count += 1
            continue

        existing_post = db.scalar(
            select(Post).where(
                Post.source == post_input.source,
                Post.source_post_id == post_input.source_post_id,
            )
        )
        if existing_post is not None:
            skipped_count += 1
            continue

        post = Post(
            person_id=_find_person_id(db, post_input.author_profile_url),
            source=post_input.source,
            source_post_id=post_input.source_post_id,
            linkedin_url=post_input.linkedin_url,
            author_name=post_input.author_name,
            author_profile_url=post_input.author_profile_url,
            content=post_input.content,
            post_type=post_input.post_type,
            authored_at=_as_naive_utc(post_input.authored_at),
            raw_json=json.dumps(post_input.raw, sort_keys=True),
        )
        db.add(post)
        inserted_count += 1

    db.commit()
    return IngestResult(inserted_count=inserted_count, skipped_count=skipped_count)


def _find_person_id(db: Session, author_profile_url: str | None) -> int | None:
    if not author_profile_url:
        return None

    canonical_author_url = _canonical_url(author_profile_url)
    people = db.scalars(select(Person)).all()
    for person in people:
        if _canonical_url(person.linkedin_url) == canonical_author_url:
            return person.id
    return None


def _canonical_url(url: str) -> str:
    return url.rstrip("/") + "/"


def _as_naive_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
