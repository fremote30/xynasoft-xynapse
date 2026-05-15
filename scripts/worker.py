# scripts/worker.py
from __future__ import annotations

import os
import time
import traceback
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError, DBAPIError

from audit.logger import log_event
from storage.jobs import claim_next_job, set_job_succeeded, set_job_failed
from storage.files import get_document_file_bytes
from storage.documents_update import update_document_text, delete_chunks_for_doc
from storage.queries import insert_chunks
from utils.chunking import chunk_text
from ingestion.ocr import ocr_pdf_bytes

load_dotenv(".env")

# Controls
SLEEP_SECONDS = float(os.getenv("WORKER_SLEEP_SECONDS") or "1.5")
JOBS_DEV_RUN = (os.getenv("JOBS_DEV_RUN") or os.getenv("JOBS_DEV_RUN") or "true").lower() in ("1", "true", "yes", "y", "on")

# Only jobs this worker will claim
ALLOWED_TYPES = ["ocr_pdf"]

# Backoff on transient failures (DB temporarily down, etc.)
MAX_BACKOFF_SECONDS = float(os.getenv("WORKER_MAX_BACKOFF_SECONDS") or "10.0")


def _now_msg(msg: str) -> None:
    # keep stdout simple for docker logs
    print(msg, flush=True)


def _safe_str(x: Any, max_len: int = 2000) -> str:
    s = str(x)
    return s if len(s) <= max_len else s[:max_len] + "…"


def run_ocr_pdf_job(job: Dict[str, Any]) -> None:
    job_id = str(job["id"])
    payload = job.get("payload") or {}

    doc_id = payload.get("document_id")
    file_id = payload.get("file_id")
    if not doc_id or not file_id:
        raise RuntimeError("OCR job payload missing document_id/file_id")

    rec = get_document_file_bytes(file_id)
    if not rec:
        raise RuntimeError(f"document_files not found for file_id={file_id}")

    pdf_bytes = rec.get("data")
    if not pdf_bytes:
        raise RuntimeError(f"document_files.data is empty for file_id={file_id}")

    # OCR
    text_out = ocr_pdf_bytes(pdf_bytes)
    text_out = (text_out or "").strip()
    if not text_out:
        raise RuntimeError("OCR completed but returned empty text")

    # Save OCR text onto document
    update_document_text(doc_id, text_out)

    # Rebuild chunks
    delete_chunks_for_doc(doc_id)
    chunks = chunk_text(text_out, chunk_size=1200, overlap=150)
    insert_chunks(doc_id, chunks)

    log_event(
        "worker_job_succeeded",
        {
            "job_id": job_id,
            "job_type": "ocr_pdf",
            "document_id": doc_id,
            "file_id": file_id,
            "chars": len(text_out),
            "chunks": len(chunks),
        },
    )


def run_job(job: Dict[str, Any]) -> None:
    job_type = job.get("job_type") or job.get("type")
    if job_type == "ocr_pdf":
        return run_ocr_pdf_job(job)

    # If something slips through, we fail it safely
    raise RuntimeError(f"Unsupported job_type={job_type}")


def main() -> None:
    if not JOBS_DEV_RUN:
        _now_msg("Worker disabled (JOBS_DEV_RUN=false). Exiting.")
        return

    _now_msg(f"Worker started. Polling for queued jobs... allowed={ALLOWED_TYPES}")

    backoff = 0.0
    while True:
        try:
            job: Optional[Dict[str, Any]] = claim_next_job(ALLOWED_TYPES)

            # Reset backoff after a successful DB round-trip
            backoff = 0.0

            if not job:
                time.sleep(SLEEP_SECONDS)
                continue

            job_id = str(job["id"])
            job_type = job.get("job_type") or job.get("type")

            try:
                run_job(job)
                set_job_succeeded(job_id)
                _now_msg(f"[OK] job {job_id} ({job_type}) succeeded")

            except Exception as e:
                # capture traceback for logs (truncate for DB storage)
                tb = traceback.format_exc()
                msg = _safe_str(e, 1000)

                # Store concise error in DB, full traceback in audit log
                set_job_failed(job_id, msg)
                log_event(
                    "worker_job_failed",
                    {
                        "job_id": job_id,
                        "job_type": job_type,
                        "error": msg,
                        "traceback": _safe_str(tb, 8000),
                        "payload": job.get("payload") or {},
                    },
                )
                _now_msg(f"[FAIL] job {job_id} ({job_type}) failed: {msg}")

        except (OperationalError, DBAPIError) as db_err:
            # DB temporarily unavailable; back off and retry
            backoff = min(MAX_BACKOFF_SECONDS, backoff * 2 + 0.5) if backoff else 0.5
            _now_msg(f"[DB] transient error, backing off {backoff:.1f}s: {_safe_str(db_err, 400)}")
            time.sleep(backoff)

        except Exception as fatal:
            # Unexpected top-level error; don't tight-loop
            backoff = min(MAX_BACKOFF_SECONDS, backoff * 2 + 0.5) if backoff else 1.0
            _now_msg(f"[FATAL] worker loop error, backing off {backoff:.1f}s: {_safe_str(fatal, 400)}")
            time.sleep(backoff)


if __name__ == "__main__":
    main()
