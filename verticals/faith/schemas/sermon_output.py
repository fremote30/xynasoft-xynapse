from pydantic import BaseModel, Field
from typing import List, Dict, Any
class PassageOverview(BaseModel):
    author: str = ""
    historical_context: str = ""
    original_audience: str = ""
    literary_genre: str = ""

class TheologicalSummary(BaseModel):
    core_message: str = ""
    doctrinal_themes: List[str] = Field(default_factory=list)
    christ_centered_insight: str = ""

class VerseBreakdownItem(BaseModel):
    verse_range: str = ""
    explanation: str = ""

class SermonPoint(BaseModel):
    point_title: str = ""
    explanation: str = ""
    supporting_scriptures: List[str] = Field(default_factory=list)

class SermonStructure(BaseModel):
    title: str = ""
    main_points: List[SermonPoint] = Field(default_factory=list)

class GhanaApplicationItem(BaseModel):
    context_type: str = ""
    application: str = ""

class SermonOutput(BaseModel):
    passage_overview: PassageOverview = Field(default_factory=PassageOverview)
    theological_summary: TheologicalSummary = Field(default_factory=TheologicalSummary)
    verse_breakdown: List[VerseBreakdownItem] = Field(default_factory=list)
    sermon_structure: SermonStructure = Field(default_factory=SermonStructure)
    ghana_application: List[GhanaApplicationItem] = Field(default_factory=list)
    illustrations: List[str] = Field(default_factory=list)
    closing_prayer: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)