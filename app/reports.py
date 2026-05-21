import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyReport, Post


@dataclass(frozen=True)
class ReportGenerationResult:
    report_id: int


def generate_daily_report(
    db: Session,
    *,
    now: datetime | None = None,
    lookback: timedelta = timedelta(hours=24),
) -> ReportGenerationResult:
    now = now or datetime.now(UTC)
    report_date = now.date()
    cutoff = now.astimezone(UTC).replace(tzinfo=None) - lookback
    recent_posts = db.scalars(
        select(Post).where(Post.authored_at >= cutoff).order_by(Post.authored_at.desc())
    ).all()

    post_count = len(recent_posts)
    post_word = "post" if post_count == 1 else "posts"
    summary_text = f"Mock summary for {post_count} recent LinkedIn {post_word}."
    themes_json = json.dumps(_mock_themes(recent_posts))
    notable_posts_json = json.dumps(_notable_posts(recent_posts))

    report = db.scalar(select(DailyReport).where(DailyReport.report_date == report_date))
    if report is None:
        report = DailyReport(
            report_date=report_date,
            post_count=post_count,
            summary_text=summary_text,
            themes_json=themes_json,
            notable_posts_json=notable_posts_json,
        )
        db.add(report)
    else:
        report.post_count = post_count
        report.summary_text = summary_text
        report.themes_json = themes_json
        report.notable_posts_json = notable_posts_json

    db.commit()
    db.refresh(report)
    return ReportGenerationResult(report_id=report.id)


def _mock_themes(posts: list[Post]) -> list[dict[str, object]]:
    if not posts:
        return []
    return [{"theme": "AI", "confidence": 1.0, "post_count": len(posts)}]


def _notable_posts(posts: list[Post]) -> list[dict[str, str | None]]:
    return [
        {
            "author_name": post.author_name,
            "content": post.content,
            "linkedin_url": post.linkedin_url,
        }
        for post in posts
    ]
