from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from typing import Dict

import os
import uuid

# 🔐 AUTH
from api.core.dependencies import (
    get_current_user
)

# 🧠 AI REWRITE
from api.services.ai_service import (

    rewrite_uploaded_sermon
)

router = APIRouter()

# =========================================
# SAFE IMPORTS
# =========================================
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None


# =========================================
# CONFIG
# =========================================
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

ALLOWED_TYPES = [
    ".pdf",
    ".docx",
    ".txt"
]


# =========================================
# PDF EXTRACTOR
# =========================================
def extract_pdf(file_path: str) -> str:

    if not PdfReader:

        raise HTTPException(
            500,
            "PDF support not installed"
        )

    text = ""

    reader = PdfReader(file_path)

    for page in reader.pages:

        text += (
            page.extract_text() or ""
        )

    return text


# =========================================
# DOCX EXTRACTOR
# =========================================
def extract_docx(file_path: str) -> str:

    if not docx:

        raise HTTPException(
            500,
            "DOCX support not installed"
        )

    doc = docx.Document(file_path)

    return "\n".join(
        [p.text for p in doc.paragraphs]
    )


# =========================================
# TXT EXTRACTOR
# =========================================
def extract_txt(file_path: str) -> str:

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read()

    except UnicodeDecodeError:

        with open(
            file_path,
            "r",
            encoding="latin-1"
        ) as f:

            return f.read()


# =========================================
# 🔒 UPLOAD + AI REWRITE
# =========================================
@router.post("/upload-sermon")
async def upload_sermon(

    file: UploadFile = File(...),

    user=Depends(
        get_current_user
    )

) -> Dict:

    # =====================================
    # VALIDATE FILE
    # =====================================
    if not file.filename:

        raise HTTPException(
            400,
            "No file provided"
        )

    filename = (
        file.filename.lower()
    )

    # =====================================
    # FILE TYPE CHECK
    # =====================================
    if not any(

        filename.endswith(ext)

        for ext in ALLOWED_TYPES

    ):

        raise HTTPException(
            400,
            "Unsupported file type"
        )

    # =====================================
    # FILE SIZE CHECK
    # =====================================
    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:

        raise HTTPException(
            400,
            "File too large (max 5MB)"
        )

    # =====================================
    # SAFE TEMP FILE
    # =====================================
    temp_filename = (

        f"temp_"
        f"{uuid.uuid4().hex}_"
        f"{filename}"

    )

    temp_path = os.path.join(
        "/tmp",
        temp_filename
    )

    with open(temp_path, "wb") as f:

        f.write(contents)

    try:

        # =================================
        # FILE TYPE HANDLING
        # =================================
        if filename.endswith(".pdf"):

            text = extract_pdf(
                temp_path
            )

        elif filename.endswith(".docx"):

            text = extract_docx(
                temp_path
            )

        elif filename.endswith(".txt"):

            text = extract_txt(
                temp_path
            )

        else:

            raise HTTPException(
                400,
                "Unsupported file type"
            )

        # =================================
        # CLEAN TEXT
        # =================================
        text = (
            text or ""
        ).strip()

        if not text:

            raise HTTPException(
                400,
                "Could not extract text"
            )

        # =================================
        # MOBILE SAFE LIMIT
        # =================================
        cleaned_text = text[:12000]

        # =================================
        # AI REWRITE
        # =================================
        rewritten = (
            rewrite_uploaded_sermon(
                cleaned_text
            )
        )

        # =================================
        # RESPONSE
        # =================================
        return {

            "success": True,

            "sermon":
                rewritten,

            "uploaded_by":
                user.id,

            "filename":
                filename
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            500,
            f"Upload failed: {str(e)}"
        )

    finally:

        # =================================
        # CLEANUP
        # =================================
        if os.path.exists(temp_path):

            os.remove(temp_path)