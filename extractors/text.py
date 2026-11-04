from __future__ import annotations

def extract_text_from_txt_bytes(data: bytes) -> str:
    """
    Extract text from plain-text bytes.
    Tries utf-8 first, then falls back safely.
    """
    if data is None:
        return ""

    # Try UTF-8 first
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # Fallback: latin-1 (won't error, may be imperfect)
    try:
        return data.decode("latin-1")
    except Exception:
        # Last resort: replace bad chars
        return data.decode("utf-8", errors="replace")
