from app.daily_cycle import format_daily_cycle_recap, run_daily_cycle
from app.db import SessionLocal, create_db


def main() -> None:
    create_db()
    with SessionLocal() as db:
        result = run_daily_cycle(db)
    print(format_daily_cycle_recap(result))


if __name__ == "__main__":
    main()
