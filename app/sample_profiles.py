from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.people import add_tracked_profile


@dataclass(frozen=True)
class SampleProfile:
    full_name: str
    linkedin_url: str
    blurb: str
    tags: tuple[str, ...]


SAMPLE_PROFILES = (
    SampleProfile(
        full_name="Arthur Brooks",
        linkedin_url="https://www.linkedin.com/in/arthur-c-brooks/",
        blurb="Author, Harvard professor, and speaker on happiness, leadership, and purpose.",
        tags=("leadership", "happiness", "purpose"),
    ),
    SampleProfile(
        full_name="Daniel Pink",
        linkedin_url="https://www.linkedin.com/in/danielpink/",
        blurb="Author and speaker focused on work, motivation, timing, and human behavior.",
        tags=("work", "motivation", "behavior"),
    ),
    SampleProfile(
        full_name="Dharmesh Shah",
        linkedin_url="https://www.linkedin.com/in/dharmesh/",
        blurb="HubSpot co-founder sharing ideas on startups, AI, culture, and product building.",
        tags=("startups", "ai", "culture"),
    ),
)


def seed_sample_profiles(db: Session) -> list[int]:
    seeded_ids: list[int] = []
    for profile in SAMPLE_PROFILES:
        person = add_tracked_profile(
            db,
            linkedin_url=profile.linkedin_url,
            full_name=profile.full_name,
            company=profile.blurb,
            tags=profile.tags,
        )
        seeded_ids.append(person.id)
    return seeded_ids
