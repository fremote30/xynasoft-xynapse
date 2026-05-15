# audit/logger.py

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from storage.db import engine


def log_event(endpoint: str, details: dict[str, Any] | None = None) -> None:
    """
    Write a simple audit log row.

    - Works for SQLite and Postgres
    - UUID generated in Python (avoids pgcrypto dependency for IDs)
    - details stored as JSON string for maximum portability
    """
    payload = details or {}

    # Helpful default fields
    payload.setdefault("ts", datetime.now(timezone.utc).isoformat())

    details_json = json.dumps(payload, ensure_ascii=False)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO audit_logs (id, endpoint, details)
                VALUES (:id, :endpoint, :details)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "endpoint": endpoint,
                "details": details_json,
            },
        )
