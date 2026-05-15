from __future__ import annotations

from bs4 import BeautifulSoup


def extract_text_from_html_bytes(html_bytes: bytes) -> str:
    """
    Extract readable text from HTML.
    Removes script/style/noscript, returns normalized text.
    """
    # Decode bytes
    try:
        html = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        html = html_bytes.decode("utf-8", errors="replace")

    soup = BeautifulSoup(html, "lxml")  # falls back if lxml missing

    # Remove non-content
    for tag in soup(["script", "style", "noscript", "svg", "canvas"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # Normalize whitespace
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines).strip()
