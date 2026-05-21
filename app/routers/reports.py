from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DailyReport
from app.reports import generate_daily_report

router = APIRouter()


class DailyReportGenerateRequest(BaseModel):
    now: datetime | None = None


class DailyReportRead(BaseModel):
    id: int
    report_date: str
    post_count: int
    summary_text: str


@router.post("/reports/daily", response_model=DailyReportRead, status_code=status.HTTP_201_CREATED)
def create_daily_report(
    payload: DailyReportGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DailyReportRead:
    result = generate_daily_report(db, now=payload.now)
    report = db.get_one(DailyReport, result.report_id)
    return DailyReportRead(
        id=report.id,
        report_date=report.report_date.isoformat(),
        post_count=report.post_count,
        summary_text=report.summary_text,
    )
