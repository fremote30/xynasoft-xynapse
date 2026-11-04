# storage/files.py
from __future__ import annotations

from uuid import uuid4
from sqlalchemy import text

from storage.db import engine


def insert_document_file(document_id: str, content_type: str, data: bytes) -> str:
    file_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO document_files (id, document_id, content_type, data)
                VALUES (:id, :document_id, :content_type, :data)
            """),
            {
                "id": file_id,
                "document_id": document_id,
                "content_type": content_type,
                "data": data,
            },
        )
    return file_id


def get_document_file_bytes(file_id: str) -> dict | None:
    stmt = text("""
        SELECT id, document_id, content_type, data
        FROM document_files
        WHERE id = :file_id
        LIMIT 1
    """)

    with engine.connect() as conn:
        row = conn.execute(stmt, {"file_id": file_id}).mappings().first()

    return dict(row) if row else None

