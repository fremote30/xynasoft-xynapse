from __future__ import annotations

import re
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, model_validator


DenominationKey = Literal[
    "broad_evangelical",
    "pentecostal_charismatic",
    "reformed",
    "baptist",
    "methodist_wesleyan",
    "catholic",
    "anglican",
    "seventh_day_adventist",
    "non_denom",
]


def _split_passages(raw: str) -> List[str]:
    """
    Split a single text field into multiple passages.
    Supports comma, semicolon, newline, and pipe.
    """
    if not raw:
        return []
    parts = re.split(r"[,\n;|]+", raw)
    cleaned: List[str] = []
    for p in parts:
        p = (p or "").strip()
        if p:
            cleaned.append(p)

    # de-dupe while preserving order
    seen = set()
    out: List[str] = []
    for p in cleaned:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


class SermonInput(BaseModel):
    # Backward-compatible: old UI still sends this
    passage_reference: str = Field(..., min_length=2, max_length=400)

    # NEW: optional list for multiple passages
    passage_references: Optional[List[str]] = Field(
        default=None,
        description="Optional list of passages. If provided, used as the authoritative list.",
        max_length=25,
    )

    theme: str = Field(..., min_length=2, max_length=200)

    # NEW: denomination guardrails (soft, respectful, non-argumentative)
    denomination: DenominationKey = Field(
        default="broad_evangelical",
        description="Controls guardrails (tone/phrasing/sensitive doctrine areas).",
    )

    audience_type: str = Field(default="General", max_length=50)
    local_context: str = Field(default="Other", max_length=50)
    service_type: str = Field(default="Sunday", max_length=50)
    tone: str = Field(default="Teaching", max_length=50)
    duration_minutes: int = Field(default=30, ge=5, le=120)

    @model_validator(mode="after")
    def normalize_passages(self) -> "SermonInput":
        """
        Ensure we always have a clean internal list of passages:
        - If passage_references provided: clean + de-dupe it
        - Else: derive from passage_reference by splitting
        """
        if self.passage_references is not None:
            cleaned: List[str] = []
            for x in self.passage_references:
                x = (x or "").strip()
                if x:
                    cleaned.append(x)

            seen = set()
            out: List[str] = []
            for p in cleaned:
                key = p.lower()
                if key not in seen:
                    seen.add(key)
                    out.append(p)

            # If user passed empty list, fall back to splitting passage_reference
            self.passage_references = out or _split_passages(self.passage_reference)
        else:
            self.passage_references = _split_passages(self.passage_reference)

        # Safety cap
        if self.passage_references and len(self.passage_references) > 25:
            self.passage_references = self.passage_references[:25]

        return self

    def resolved_passages(self) -> List[str]:
        return self.passage_references or _split_passages(self.passage_reference)