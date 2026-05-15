from __future__ import annotations

from email import policy
from email.parser import BytesParser

from extractors.html import extract_text_from_html_bytes


def extract_text_from_eml_bytes(eml_bytes: bytes) -> str:
    """
    Extract email subject/from/to/date + body text.
    Prefers text/plain; falls back to text/html -> text.
    """
    msg = BytesParser(policy=policy.default).parsebytes(eml_bytes)

    subject = (msg.get("subject") or "").strip()
    from_ = (msg.get("from") or "").strip()
    to_ = (msg.get("to") or "").strip()
    date = (msg.get("date") or "").strip()

    header = []
    if subject:
        header.append(f"Subject: {subject}")
    if from_:
        header.append(f"From: {from_}")
    if to_:
        header.append(f"To: {to_}")
    if date:
        header.append(f"Date: {date}")

    body_text_plain: list[str] = []
    body_text_html: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get_content_disposition() or "").lower()
            if disp == "attachment":
                continue

            try:
                payload = part.get_payload(decode=True) or b""
            except Exception:
                payload = b""

            if ctype == "text/plain":
                try:
                    body_text_plain.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
                except Exception:
                    body_text_plain.append(payload.decode("utf-8", errors="replace"))

            elif ctype == "text/html":
                body_text_html.append(extract_text_from_html_bytes(payload))
    else:
        ctype = (msg.get_content_type() or "").lower()
        payload = msg.get_payload(decode=True) or b""

        if ctype == "text/plain":
            body_text_plain.append(msg.get_content())
        elif ctype == "text/html":
            body_text_html.append(extract_text_from_html_bytes(payload))
        else:
            # fallback
            try:
                body_text_plain.append(payload.decode("utf-8", errors="replace"))
            except Exception:
                body_text_plain.append("")

    body = ""
    if body_text_plain and any(t.strip() for t in body_text_plain):
        body = "\n".join(t.strip() for t in body_text_plain if t and t.strip())
    elif body_text_html and any(t.strip() for t in body_text_html):
        body = "\n".join(t.strip() for t in body_text_html if t and t.strip())

    parts = []
    if header:
        parts.append("\n".join(header))
        parts.append("")
    if body:
        parts.append(body)

    return "\n".join(parts).strip()
