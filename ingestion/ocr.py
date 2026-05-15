from __future__ import annotations

def ocr_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    OCR a PDF (image-only/scanned) -> extracted text.

    Requires:
      pip install pdf2image pytesseract
      and system packages:
      - poppler-utils (for pdftoppm)
      - tesseract-ocr
    """
    try:
        from pdf2image import convert_from_bytes
    except Exception as e:
        raise RuntimeError(
            "pdf2image is not installed. Run: pip install pdf2image\n"
            "Also install poppler-utils (system package)."
        ) from e

    try:
        import pytesseract
    except Exception as e:
        raise RuntimeError(
            "pytesseract is not installed. Run: pip install pytesseract\n"
            "Also install tesseract-ocr (system package)."
        ) from e

    # Convert PDF pages -> PIL Images
    pages = convert_from_bytes(pdf_bytes, dpi=200)

    texts: list[str] = []
    for img in pages:
        t = pytesseract.image_to_string(img)
        if t:
            texts.append(t)

    return "\n\n".join(texts).strip()
