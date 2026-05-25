from pathlib import Path

from app.commentary_profile import (
    CommentaryProfile,
    build_comment_starter_ideas,
    load_commentary_profile,
)


def test_load_commentary_profile_returns_markdown_sections(tmp_path: Path):
    profile_path = tmp_path / "tony-commentary-style.md"
    profile_path.write_text(
        "# Tony Commentary Style\n\n"
        "Intro text.\n\n"
        "## Professional identity\n\n"
        "- Tony builds learning projects.\n\n"
        "## Avoid\n\n"
        "- Generic praise.\n",
        encoding="utf-8",
    )

    profile = load_commentary_profile(profile_path)

    assert profile == CommentaryProfile(
        path=profile_path,
        markdown=profile_path.read_text(encoding="utf-8"),
        sections={
            "Professional identity": "- Tony builds learning projects.",
            "Avoid": "- Generic praise.",
        },
        setup_message=None,
    )


def test_load_commentary_profile_returns_setup_message_when_missing(tmp_path: Path):
    profile_path = tmp_path / "missing.md"

    profile = load_commentary_profile(profile_path)

    assert profile.markdown == ""
    assert profile.sections == {}
    assert profile.setup_message == (
        f"Commentary profile not found at {profile_path}. "
        "Create docs/profile/tony-commentary-style.md to enable Tony-style comment starters."
    )


def test_build_comment_starter_ideas_uses_profile_guidance_without_copy_paste():
    profile = CommentaryProfile(
        path=Path("profile.md"),
        markdown="",
        sections={
            "Topics Tony wants to engage with": (
                "- AI and practical workflows\n"
                "- Entrepreneurship and product building"
            ),
            "Commentary principles": (
                "- Be specific to the post.\n"
                "- Ask a useful question when it opens a real conversation."
            ),
        },
        setup_message=None,
    )

    ideas = build_comment_starter_ideas(
        "AI workflows are changing how founders build products with customers.",
        profile,
    )

    assert ideas == [
        "One angle Tony might explore: connect this post to AI and practical workflows.",
        (
            "A useful question Tony could ask: what is one practical next step "
            "or tradeoff behind this idea?"
        ),
        (
            "A personal observation Tony might add: relate the post to learning "
            "in public with agent-assisted product building."
        ),
    ]


def test_build_comment_starter_ideas_returns_setup_guidance_when_profile_missing(tmp_path: Path):
    profile = CommentaryProfile(
        path=tmp_path / "missing.md",
        markdown="",
        sections={},
        setup_message="Create the profile first.",
    )

    ideas = build_comment_starter_ideas("A post about leadership.", profile)

    assert ideas == ["Create the profile first."]
