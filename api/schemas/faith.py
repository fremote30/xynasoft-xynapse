from pydantic import BaseModel
from typing import List


class SermonPoint(BaseModel):
    title: str
    content: str


class SermonResponse(BaseModel):
    title: str
    scripture: str
    introduction: str
    main_points: List[SermonPoint]
    application: str
    conclusion: str

class SermonRequest(BaseModel):
    input: str
    scripture: str = ""
    denomination: str = "general"
    audience: str = ""
    context: str = ""
    tone: str = "balanced"
    duration: str = "30"

class SermonRefineRequest(BaseModel):
    sermon: dict
    refine_type: str