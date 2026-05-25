from pathlib import Path

from app.commentary_profile import CommentaryProfile, load_commentary_profile


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
