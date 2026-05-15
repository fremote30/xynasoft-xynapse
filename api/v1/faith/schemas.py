from pydantic import BaseModel
from typing import List, Optional


class AskRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    top_k: int = 5


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    preview: str


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]
    model: str
