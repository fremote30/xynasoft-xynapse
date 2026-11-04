from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple
import os


# --- Import per-type extractors (keep these lightweight) ---
from extractors.text import extract_text_from_txt_bytes
from extractors.docx import extract_text_from_docx_bytes
from extractors.xlsx import extract_text_from_xlsx_bytes
from extractors.html import extract_text_from_html_bytes
from extractors.eml import extract_text_from_eml_bytes

# IMPORTANT: keep PDFs working exactly as-is.
# Adjust this import path to YOUR existing pdf extractor location.
# You mentioned you have PDF ingestion already working; point to that.
try:
    from ingestion.pdf import extract_text_from_pdf_bytes  # common
except Exception:
    try:
        from ingest.pdf import extract_text_from_pdf_bytes  # older name
    except Exception:
        # If your PDF extractor lives elsewhere, update this import.
        extract_text_from_pdf_bytes = None


@dataclass(frozen=True)
class ExtractResult:
    text: str
    kind: str   # <- add this
    mime: str
    ext: str


ExtractorFn = Callable[[bytes], str]


def _guess_ext_and_mime(filename: str, content_type: Optional[str]) -> Tuple[str, str]:
    name = (filename or "").lower().strip()
    ext = os.path.splitext(name)[1].lstrip(".") if "." in name else ""

    mime = (content_type or "").lower().strip()

    # Normalize common MIME types to extensions
    if not ext:
        if "pdf" in mime:
            ext = "pdf"
        elif "word" in mime or "officedocument.wordprocessingml" in mime:
            ext = "docx"
        elif "spreadsheetml" in mime or "excel" in mime:
            ext = "xlsx"
        elif "html" in mime:
            ext = "html"
        elif "message/rfc822" in mime or "rfc822" in mime:
            ext = "eml"
        elif "text/plain" in mime:
            ext = "txt"

    # If mime is missing, fill a best-effort guess
    if not mime:
        mime_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "html": "text/html",
            "htm": "text/html",
            "eml": "message/rfc822",
            "txt": "text/plain",
        }
        mime = mime_map.get(ext, "application/octet-stream")

    return ext, mime


def _build_registry() -> Dict[str, ExtractorFn]:
    reg: Dict[str, ExtractorFn] = {
        "txt": extract_text_from_txt_bytes,
        "docx": extract_text_from_docx_bytes,
        "xlsx": extract_text_from_xlsx_bytes,
        "html": extract_text_from_html_bytes,
        "htm": extract_text_from_html_bytes,
        "eml": extract_text_from_eml_bytes,
    }
    if extract_text_from_pdf_bytes is not None:
        reg["pdf"] = extract_text_from_pdf_bytes
    return reg


_REGISTRY = _build_registry()


def extract_text(
    *,
    filename: str,
    content_type: Optional[str] = None,
    data: Optional[bytes] = None,
    file_bytes: Optional[bytes] = None,
) -> ExtractResult:
    """
    Unified extractor entrypoint.

    Supports BOTH parameter names:
      - data=...  (what your API is currently passing)
      - file_bytes=... (older/internal name)

    Returns ExtractResult(text, mime, ext)
    """
    raw = data if data is not None else file_bytes
    if raw is None:
        raise ValueError("No file bytes provided (expected data=... or file_bytes=...).")

    ext, mime = _guess_ext_and_mime(filename, content_type)

    extractor = _REGISTRY.get(ext)
    if extractor is None:
        raise ValueError(f"Unsupported file type: .{ext} (mime={mime})")

    text = extractor(raw) or ""
    text = text.strip()
    if not text:
        raise ValueError(f"No text extracted from .{ext} file.")

    return ExtractResult(text=text, kind=ext, mime=mime, ext=ext)