import json
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.people import add_tracked_profile

router = APIRouter()


class ProfileCreate(BaseModel):
    linkedin_url: str
    full_name: str | None = None
    company: str | None = None
    tags: list[str] | None = None


class ProfileRead(BaseModel):
    id: int
    linkedin_url: str
    full_name: str | None
    company: str | None
    tags: list[str]
    is_active: bool


@router.post("/profiles", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ProfileRead:
    person = add_tracked_profile(
        db,
        linkedin_url=payload.linkedin_url,
        full_name=payload.full_name,
        company=payload.company,
        tags=payload.tags,
    )
    return ProfileRead(
        id=person.id,
        linkedin_url=person.linkedin_url,
        full_name=person.full_name,
        company=person.company,
        tags=json.loads(person.tags_json or "[]"),
        is_active=person.is_active,
    )
