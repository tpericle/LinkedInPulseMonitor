from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.pipeline import ingest_apify_items

router = APIRouter()


class ApifyItemsIngestRequest(BaseModel):
    items: list[dict[str, Any]]
    now: datetime | None = None


class IngestSummaryRead(BaseModel):
    parsed_count: int
    inserted_count: int
    skipped_count: int


@router.post(
    "/ingest/apify-items",
    response_model=IngestSummaryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_apify_items_ingest(
    payload: ApifyItemsIngestRequest,
    db: Annotated[Session, Depends(get_db)],
) -> IngestSummaryRead:
    result = ingest_apify_items(db, payload.items, now=payload.now)
    return IngestSummaryRead(
        parsed_count=result.parsed_count,
        inserted_count=result.inserted_count,
        skipped_count=result.skipped_count,
    )
