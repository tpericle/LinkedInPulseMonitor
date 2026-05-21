import json
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Person


def add_tracked_profile(
    db: Session,
    *,
    linkedin_url: str,
    full_name: str | None = None,
    company: str | None = None,
    tags: Sequence[str] | None = None,
) -> Person:
    canonical_url = _canonical_linkedin_url(linkedin_url)
    person = _find_person_by_url(db, canonical_url)
    if person is None:
        person = Person(linkedin_url=canonical_url)
        db.add(person)

    if full_name is not None:
        person.full_name = full_name
    if company is not None:
        person.company = company
    if tags is not None:
        person.tags_json = json.dumps(list(tags))
    person.is_active = True

    db.commit()
    db.refresh(person)
    return person


def _find_person_by_url(db: Session, canonical_url: str) -> Person | None:
    people = db.scalars(select(Person)).all()
    for person in people:
        if _canonical_linkedin_url(person.linkedin_url) == canonical_url:
            return person
    return None


def _canonical_linkedin_url(url: str) -> str:
    return url.strip().rstrip("/") + "/"
