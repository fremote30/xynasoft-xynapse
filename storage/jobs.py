# storage/jobs.py
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from storage.db import engine


# -------------------------
# Create / Enqueue Job
# -------------------------

def enqueue_job(job_type: str, payload: Dict[str, Any]) -> str:
    job_id = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO jobs (id, job_type, status, payload, created_at, updated_at)
                VALUES (:id, :job_type, 'queued', :payload::jsonb, now(), now())
            """),
            {"id": job_id, "job_type": job_type, "payload": payload},
        )

    return job_id


# -------------------------
# Fetch Job
# -------------------------

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM jobs WHERE id = :id"),
            {"id": job_id},
        ).mappings().first()
    return dict(row) if row else None


def list_jobs(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT *
                FROM jobs
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": int(limit), "offset": int(offset)},
        ).mappings().all()
    return [dict(r) for r in rows]


# -------------------------
# Worker: Claim Next Job
# -------------------------

def claim_next_job(allowed_types: List[str]) -> Optional[Dict[str, Any]]:
    """
    Atomically claim next queued job of allowed types.
    Uses FOR UPDATE SKIP LOCKED to allow multiple workers.
    """
    allowed_types = [t for t in (allowed_types or []) if t]
    if not allowed_types:
        return None

    # IMPORTANT:
    # Do NOT do ANY(:types::text[]) because psycopg2 chokes on :param::cast.
    # Instead use ANY(ARRAY[:types]::text[]) and pass a Python list.
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT *
                FROM jobs
                WHERE status = 'queued'
                  AND job_type = ANY(ARRAY[:types]::text[])
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """),
            {"types": allowed_types},
        ).mappings().first()

        if not row:
            return None

        conn.execute(
            text("""
                UPDATE jobs
                SET status = 'running',
                    updated_at = now()
                WHERE id = :id
            """),
            {"id": row["id"]},
        )

        return dict(row)


# -------------------------
# Status Updates
# -------------------------

def set_job_running(job_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE jobs
                SET status = 'running',
                    updated_at = now()
                WHERE id = :id
            """),
            {"id": job_id},
        )


def set_job_succeeded(job_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE jobs
                SET status = 'succeeded',
                    updated_at = now()
                WHERE id = :id
            """),
            {"id": job_id},
        )


def set_job_failed(job_id: str, error: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE jobs
                SET status = 'failed',
                    error = :error,
                    updated_at = now()
                WHERE id = :id
            """),
            {"id": job_id, "error": error},
        )
