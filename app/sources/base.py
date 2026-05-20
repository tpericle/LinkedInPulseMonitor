from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PostInput:
    source: str
    source_post_id: str | None
    linkedin_url: str | None
    author_name: str | None
    author_profile_url: str | None
    content: str
    post_type: str
    authored_at: datetime | None
    raw: dict[str, Any]
