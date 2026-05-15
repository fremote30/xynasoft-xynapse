# verticals/faith/storage/public_store.py
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> str:
    # Keeps Faith isolated; defaults to local file in project root or env override
    return os.getenv("XYNASOFT_FAITH_DB", "xynasoft_faith.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_faith_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faith_shared_sermons (
              share_id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              title TEXT NOT NULL,
              payload_input TEXT NOT NULL,
              payload_output TEXT NOT NULL,
              payload_manuscript TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faith_member_questions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              share_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              name TEXT,
              question TEXT NOT NULL,
              FOREIGN KEY (share_id) REFERENCES faith_shared_sermons(share_id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_share(
    *,
    title: str,
    payload_input: Dict[str, Any],
    payload_output: Dict[str, Any],
    payload_manuscript: Optional[Dict[str, Any]] = None,
) -> str:
    init_faith_db()

    share_id = uuid.uuid4().hex[:12]  # short link token
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO faith_shared_sermons
              (share_id, created_at, title, payload_input, payload_output, payload_manuscript)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                share_id,
                _utc_now(),
                title.strip() or "Shared Sermon",
                json.dumps(payload_input, ensure_ascii=False),
                json.dumps(payload_output, ensure_ascii=False),
                json.dumps(payload_manuscript, ensure_ascii=False) if payload_manuscript else None,
            ),
        )
        conn.commit()
        return share_id
    finally:
        conn.close()


def get_share(share_id: str) -> Optional[Dict[str, Any]]:
    init_faith_db()

    conn = _connect()
    try:
        row = conn.execute(
            "SELECT share_id, created_at, title, payload_input, payload_output, payload_manuscript FROM faith_shared_sermons WHERE share_id = ?",
            (share_id,),
        ).fetchone()
        if not row:
            return None

        def _loads(s: Optional[str]) -> Optional[Dict[str, Any]]:
            if not s:
                return None
            try:
                return json.loads(s)
            except Exception:
                return None

        return {
            "share_id": row["share_id"],
            "created_at": row["created_at"],
            "title": row["title"],
            "payload_input": _loads(row["payload_input"]) or {},
            "payload_output": _loads(row["payload_output"]) or {},
            "payload_manuscript": _loads(row["payload_manuscript"]) if row["payload_manuscript"] else None,
        }
    finally:
        conn.close()


def add_question(*, share_id: str, name: Optional[str], question: str) -> int:
    init_faith_db()

    conn = _connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO faith_member_questions (share_id, created_at, name, question)
            VALUES (?, ?, ?, ?)
            """,
            (share_id, _utc_now(), (name or None), question.strip()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def count_questions(share_id: str) -> int:
    init_faith_db()

    conn = _connect()
    try:
        row = conn.execute(
            "SELECT COUNT(1) AS c FROM faith_member_questions WHERE share_id = ?",
            (share_id,),
        ).fetchone()
        return int(row["c"] or 0) if row else 0
    finally:
        conn.close()