from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_COMMENTARY_PROFILE_PATH = Path("docs/profile/tony-commentary-style.md")


@dataclass(frozen=True)
class CommentaryProfile:
    path: Path
    markdown: str
    sections: dict[str, str]
    setup_message: str | None = None


def load_commentary_profile(
    path: Path | str = DEFAULT_COMMENTARY_PROFILE_PATH,
) -> CommentaryProfile:
    profile_path = Path(path)
    if not profile_path.exists():
        return CommentaryProfile(
            path=profile_path,
            markdown="",
            sections={},
            setup_message=(
                f"Commentary profile not found at {profile_path}. "
                "Create docs/profile/tony-commentary-style.md to enable "
                "Tony-style comment starters."
            ),
        )

    markdown = profile_path.read_text(encoding="utf-8")
    return CommentaryProfile(
        path=profile_path,
        markdown=markdown,
        sections=_parse_second_level_sections(markdown),
        setup_message=None,
    )


def _parse_second_level_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", markdown, flags=re.MULTILINE))
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[title] = markdown[start:end].strip()
    return sections
