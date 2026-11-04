from io import BytesIO
from pypdf import PdfReader

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))  # ← THIS IS THE FIX
    texts = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            texts.append(text)

    return "\n\n".join(texts).strip()
