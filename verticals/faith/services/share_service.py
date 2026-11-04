from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from verticals.faith.schemas.sermon_input import SermonInput
from verticals.faith.schemas.sermon_output import SermonOutput
from verticals.faith.schemas.sermon_manuscript import ManuscriptResponse


# Simple file storage (demo-ready)
DATA_DIR = Path("storage/faith")
SHARES_DIR = DATA_DIR / "shares"
QUESTIONS_DIR = DATA_DIR / "questions"

SHARES_DIR.mkdir(parents=True, exist_ok=True)
QUESTIONS_DIR.mkdir(parents=True, exist_ok=True)


class PublishRequest(BaseModel):
  sermon_input: SermonInput
  sermon_output: SermonOutput
  manuscript: Optional[Dict[str, Any]] = None  # store raw manuscript JSON (from ManuscriptResponse)


class PublishResponse(BaseModel):
  share_id: str
  share_path: str
  share_url: str
  created_at: str


class PublicSermonResponse(BaseModel):
  share_id: str
  title: str
  created_at: str
  payload_input: Dict[str, Any]
  payload_output: Dict[str, Any]
  manuscript: Optional[Dict[str, Any]] = None


class QuestionIn(BaseModel):
  name: Optional[str] = None
  question: str


def _now_iso() -> str:
  return datetime.now(timezone.utc).isoformat()


def _new_share_id() -> str:
  # short + URL-safe
  return secrets.token_urlsafe(6).replace("-", "").replace("_", "")


def _share_file(share_id: str) -> Path:
  return SHARES_DIR / f"{share_id}.json"


def _questions_file(share_id: str) -> Path:
  return QUESTIONS_DIR / f"{share_id}.jsonl"


async def publish_sermon(req: PublishRequest, base_url: str) -> PublishResponse:
  share_id = _new_share_id()
  created_at = _now_iso()

  # Title heuristic (member page can show this)
  title = ""
  try:
    title = req.sermon_output.sermon_structure.title or ""
  except Exception:
    title = ""

  record: Dict[str, Any] = {
    "share_id": share_id,
    "created_at": created_at,
    "title": title or "Shared Sermon",
    "payload_input": req.sermon_input.model_dump(),
    "payload_output": req.sermon_output.model_dump(),
    "manuscript": req.manuscript,  # already JSON
  }

  _share_file(share_id).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

  share_path = f"/faith/church/{share_id}"
  share_url = f"{base_url.rstrip('/')}{share_path}"

  return PublishResponse(
    share_id=share_id,
    share_path=share_path,
    share_url=share_url,
    created_at=created_at,
  )


async def get_public_sermon(share_id: str) -> PublicSermonResponse:
  fp = _share_file(share_id)
  if not fp.exists():
    raise FileNotFoundError("Share not found")

  data = json.loads(fp.read_text(encoding="utf-8"))

  return PublicSermonResponse(
    share_id=data["share_id"],
    title=data.get("title") or "Shared Sermon",
    created_at=data.get("created_at") or "",
    payload_input=data.get("payload_input") or {},
    payload_output=data.get("payload_output") or {},
    manuscript=data.get("manuscript"),
  )


async def add_question(share_id: str, q: QuestionIn) -> Dict[str, Any]:
  # Ensure share exists
  fp = _share_file(share_id)
  if not fp.exists():
    raise FileNotFoundError("Share not found")

  row = {
    "received_at": _now_iso(),
    "name": (q.name or "").strip() or None,
    "question": (q.question or "").strip(),
  }
  if not row["question"]:
    raise ValueError("Question is required")

  qfp = _questions_file(share_id)
  with qfp.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")

  return {"ok": True}