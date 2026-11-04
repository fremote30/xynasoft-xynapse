from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import text
from storage.db import engine


def _new_id() -> str:
    return secrets.token_urlsafe(16)


def insert_faith_question(*, sermon_id: str, name: str | None, question: str) -> str:
    qid = _new_id()
    q = text(
        """
        INSERT INTO faith_questions (id, sermon_id, name, question)
        VALUES (:id, :sermon_id, :name, :question)
        """
    )
    with engine.begin() as conn:
        conn.execute(q, {"id": qid, "sermon_id": sermon_id, "name": name, "question": question})
    return qid


def list_faith_questions(*, sermon_id: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    q = text(
        """
        SELECT id, sermon_id, name, question, created_at
        FROM faith_questions
        WHERE sermon_id = :sermon_id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(q, {"sermon_id": sermon_id, "limit": limit, "offset": offset}).mappings().all()
    return [dict(r) for r in rows]