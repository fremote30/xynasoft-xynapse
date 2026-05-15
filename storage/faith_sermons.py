from __future__ import annotations

import json
import secrets
import string
from typing import Any

from psycopg2.extras import Json
from sqlalchemy import text

from storage.db import engine


def _new_id() -> str:
    return secrets.token_urlsafe(16)


def _new_share_id(length: int = 10) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def insert_faith_sermon(
    *,
    title: str,
    payload_input: dict[str, Any],
    payload_output: dict[str, Any],
    pastor_id: str | None = None,
) -> str:
    sermon_id = _new_id()

    q = text(
        """
        INSERT INTO faith_sermons (id, pastor_id, title, payload_input, payload_output, is_published)
        VALUES (:id, :pastor_id, :title, :payload_input, :payload_output, false)
        """
    )

    with engine.begin() as conn:
        conn.execute(
            q,
            {
                "id": sermon_id,
                "pastor_id": pastor_id,
                "title": title,
                "payload_input": Json(payload_input),
                "payload_output": Json(payload_output),
            },
        )

    return sermon_id


def list_faith_sermons(*, limit: int = 50, offset: int = 0, pastor_id: str | None = None) -> list[dict[str, Any]]:
    where = "WHERE pastor_id = :pastor_id" if pastor_id else ""
    q = text(
        f"""
        SELECT id, pastor_id, title, is_published, share_id, created_at
        FROM faith_sermons
        {where}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
    )
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if pastor_id:
        params["pastor_id"] = pastor_id

    with engine.begin() as conn:
        rows = conn.execute(q, params).mappings().all()
    return [dict(r) for r in rows]


def publish_faith_sermon(*, sermon_id: str) -> dict[str, Any]:
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT id FROM faith_sermons WHERE id=:id"), {"id": sermon_id}).scalar()
        if not exists:
            raise ValueError("Sermon not found")

        row = conn.execute(text("SELECT share_id FROM faith_sermons WHERE id=:id"), {"id": sermon_id}).mappings().first()
        if row and row.get("share_id"):
            return {"sermon_id": sermon_id, "share_id": row["share_id"]}

        for _ in range(8):
            share_id = _new_share_id()
            try:
                conn.execute(
                    text("UPDATE faith_sermons SET is_published=true, share_id=:share_id WHERE id=:id"),
                    {"id": sermon_id, "share_id": share_id},
                )
                return {"sermon_id": sermon_id, "share_id": share_id}
            except Exception:
                continue

    raise RuntimeError("Could not publish sermon (share_id collision retries exceeded)")


def get_public_sermon_by_share_id(*, share_id: str) -> dict[str, Any] | None:
    q = text(
        """
        SELECT id, title, payload_output, created_at
        FROM faith_sermons
        WHERE share_id = :share_id AND is_published = true
        """
    )
    with engine.begin() as conn:
        row = conn.execute(q, {"share_id": share_id}).mappings().first()
    if not row:
        return None

    rec = dict(row)
    if isinstance(rec.get("payload_output"), str):
        try:
            rec["payload_output"] = json.loads(rec["payload_output"])
        except Exception:
            pass
    return rec