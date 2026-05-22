from app.db import SessionLocal, create_db
from app.sample_profiles import SAMPLE_PROFILES, seed_sample_profiles


def main() -> None:
    create_db()
    with SessionLocal() as db:
        seeded_ids = seed_sample_profiles(db)
    print(f"Seeded {len(seeded_ids)} active sample profiles:")
    for profile in SAMPLE_PROFILES:
        print(f"- {profile.full_name}: {profile.linkedin_url}")


if __name__ == "__main__":
    main()
