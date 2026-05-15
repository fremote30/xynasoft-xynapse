from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _get_db_url() -> str:
    # Always load .env when running as a script
    load_dotenv(".env")

    # Prefer LOCAL when available (host tools / alembic / pytest)
    url = os.getenv("DATABASE_URL_LOCAL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_LOCAL or DATABASE_URL must be set (check .env).")
    return url


def main() -> None:
    url = _get_db_url()
    engine = create_engine(url, future=True)

    deadline = time.time() + 30
    last_err: Exception | None = None

    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("DB is ready")
            return
        except Exception as e:
            last_err = e
            time.sleep(1)

    print("DB not ready after 30s")
    if last_err:
        print(last_err)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
